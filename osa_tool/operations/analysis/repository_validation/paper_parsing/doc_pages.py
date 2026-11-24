"""Lazy, disk-backed access to the rendered pages of a document.

Rendering a PDF used to mean holding every page in memory at once as a decoded
BGR array. At pdf2image's default of 200 DPI a letter page costs roughly 11 MB,
so a 60-page paper occupied ~700 MB of pages before a single element had been
described — and the batch drivers multiply that by the number of papers in
flight. On a memory-tight machine that is what the OOM killer reacts to.

:class:`PageStore` keeps the ``pages[page_num]`` / ``len(pages)`` contract the
layout and description stages rely on, but pdf2image writes the pages straight
to a temporary directory (``paths_only``) and each page is decoded only when
something asks for it, with a handful kept resident. Peak page memory becomes a
function of the cache size rather than of the document length.
"""

from __future__ import annotations

import shutil
import tempfile
import weakref
from collections import OrderedDict
from pathlib import Path
from threading import Lock

import cv2
import numpy as np
from pdf2image import convert_from_path

from osa_tool.operations.analysis.repository_validation.paper_parsing.exceptions import PageRenderError
from osa_tool.utils.logger import logger

DEFAULT_RENDER_DPI = 200
DEFAULT_PAGE_CACHE_SIZE = 4

# Lossless, and far smaller on disk than the ppm pdftoppm writes by default. The
# layout model and the VLM both read these pages, so a lossy intermediate would
# degrade detection and description quality to save temp space we do not need.
PAGE_FORMAT = "png"


class PageStore:
    """A read-only sequence of page images that lives on disk, not in RAM.

    Indexing returns the page as a BGR ``numpy`` array, exactly like the list of
    arrays this replaced, so callers doing ``pages[element["page_num"]]`` are
    unaffected. At most ``cache_size`` decoded pages are held at a time; because
    both readers (crop encoding and full-page context images) walk the document
    in page order, a small cache still hits almost every time.

    Owns the temporary directory it renders into, so :meth:`close` must be called
    — or the store used as a context manager — to reclaim the disk.
    """

    def __init__(
        self,
        page_paths: list[str | Path],
        *,
        cache_size: int = DEFAULT_PAGE_CACHE_SIZE,
        owned_dir: str | Path | None = None,
    ) -> None:
        self._paths = [Path(path) for path in page_paths]
        self._cache_size = max(1, cache_size)
        self._cache: OrderedDict[int, np.ndarray] = OrderedDict()
        self._lock = Lock()
        # Callers are expected to close(), but a rendered document is tens to
        # hundreds of MB of temp files, so a store that is simply dropped should
        # not leave them behind. finalize() also runs at interpreter exit, and is
        # idempotent, so close() can just invoke it.
        self._finalizer = weakref.finalize(self, shutil.rmtree, str(owned_dir), True) if owned_dir is not None else None

    @classmethod
    def from_pdf(
        cls,
        pdf_path: str | Path,
        *,
        dpi: int = DEFAULT_RENDER_DPI,
        cache_size: int = DEFAULT_PAGE_CACHE_SIZE,
    ) -> PageStore:
        """Rasterize ``pdf_path`` into a temporary directory, one file per page."""
        directory = Path(tempfile.mkdtemp(prefix="osa-paper-pages-"))
        try:
            paths = convert_from_path(
                str(pdf_path),
                dpi=dpi,
                output_folder=str(directory),
                fmt=PAGE_FORMAT,
                paths_only=True,
            )
        except Exception:
            shutil.rmtree(directory, ignore_errors=True)
            raise

        if not paths:
            shutil.rmtree(directory, ignore_errors=True)
            raise PageRenderError(f"Rendering {pdf_path} produced no pages")

        logger.debug("Rendered %s page(s) of %s at %s DPI into %s", len(paths), pdf_path, dpi, directory)
        # pdf2image returns the paths sorted, and pdftoppm zero-pads the page
        # counter to the document's width, so this order is the page order.
        return cls(paths, cache_size=cache_size, owned_dir=directory)

    def __len__(self) -> int:
        return len(self._paths)

    def __getitem__(self, index: int | slice) -> np.ndarray | list[np.ndarray]:
        if isinstance(index, slice):
            return [self[position] for position in range(*index.indices(len(self._paths)))]

        position = index + len(self._paths) if index < 0 else index
        if not 0 <= position < len(self._paths):
            raise IndexError(f"page {index} is out of range for a {len(self._paths)}-page document")

        with self._lock:
            page = self._cache.get(position)
            if page is not None:
                self._cache.move_to_end(position)
                return page

        # Decoded outside the lock so concurrent readers are not serialized; two
        # readers racing on the same page just decode it twice, which is cheap
        # next to holding every page resident.
        page = cv2.imread(str(self._paths[position]), cv2.IMREAD_COLOR)
        if page is None:
            raise PageRenderError(f"Could not read rendered page {position} at {self._paths[position]}")

        with self._lock:
            self._cache[position] = page
            self._cache.move_to_end(position)
            while len(self._cache) > self._cache_size:
                self._cache.popitem(last=False)
        return page

    def __iter__(self):
        for position in range(len(self._paths)):
            yield self[position]

    def save_to(self, directory: str | Path) -> list[Path]:
        """Copy the rendered pages into ``directory``, returning the new paths.

        Lets a layout run hand its pages to a later description run: the store
        itself lives in a temporary directory that is reclaimed on close, but the
        full-page context images the VLM stage needs are rebuilt from these.
        """
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        saved = []
        for position, source in enumerate(self._paths):
            target = destination / f"page-{position:04d}{source.suffix}"
            shutil.copyfile(source, target)
            saved.append(target)
        return saved

    def close(self) -> None:
        """Drop the decoded pages and delete the temporary directory.

        Idempotent, and safe to skip — the finalizer registered in ``__init__``
        does the same cleanup when the store is collected or at exit.
        """
        with self._lock:
            self._cache.clear()
        if self._finalizer is not None:
            self._finalizer()
        self._paths = []

    def __enter__(self) -> PageStore:
        return self

    def __exit__(self, *_) -> None:
        self.close()
