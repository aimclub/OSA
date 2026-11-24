"""Persist the layout stage's output so the VLM stage can run separately.

Splitting the two stages across a file on disk is what lets the batch drivers
finish all layout detection before any describing starts. That ordering matters
for more than tidiness: layout detection is synchronous CPU work that freezes the
event loop for its whole duration, so running it while another paper's VLM
requests are in flight strands those requests until they time out. Detecting
first and describing afterwards means nothing blocks the loop once requests are
being made.

Writing the report out also bounds memory — the driver holds one paper's elements
at a time instead of the whole corpus — and makes describing re-runnable without
paying for detection again.
"""

from __future__ import annotations

import json
from pathlib import Path

from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_pages import (
    DEFAULT_PAGE_CACHE_SIZE,
    PageStore,
)
from osa_tool.operations.analysis.repository_validation.paper_parsing.exceptions import LayoutDetectionError
from osa_tool.operations.analysis.repository_validation.paper_parsing.paper_utils import to_base64_str
from osa_tool.utils.logger import logger

LAYOUT_FILENAME = "layout.json"
PAGES_DIRNAME = "pages"
LAYOUT_FORMAT_VERSION = 1


def save_layout(
    report: list[dict],
    pages,
    destination: str | Path,
    *,
    source_path: str | Path,
    render_dpi: int,
) -> Path:
    """Write ``layout.json`` and the rendered pages under ``destination``.

    ``image_bytes`` is stored as a plain base64 string rather than the ``str(b'')``
    repr the older in-place serialization produced, so the file is ordinary JSON
    that anything can read.
    """
    directory = Path(destination)
    directory.mkdir(parents=True, exist_ok=True)

    page_paths = pages.save_to(directory / PAGES_DIRNAME) if len(pages) else []

    elements = []
    for element in report:
        serialized = dict(element)
        if "image_bytes" in serialized:
            serialized["image_bytes"] = to_base64_str(serialized["image_bytes"])
        elements.append(serialized)

    payload = {
        "version": LAYOUT_FORMAT_VERSION,
        "source_path": str(source_path),
        "render_dpi": render_dpi,
        "page_count": len(page_paths),
        "element_count": len(elements),
        "elements": elements,
    }
    path = directory / LAYOUT_FILENAME
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
    temporary.replace(path)
    logger.info("Layout saved: %s elements, %s pages -> %s", len(elements), len(page_paths), path)
    return path


def load_layout(destination: str | Path, *, cache_size: int = DEFAULT_PAGE_CACHE_SIZE) -> tuple[list[dict], PageStore]:
    """Read back what :func:`save_layout` wrote.

    The returned :class:`PageStore` does not own the pages directory — these
    pages belong to the output tree, not to a temporary render — so closing it
    frees the decoded cache without deleting anything.
    """
    directory = Path(destination)
    path = directory / LAYOUT_FILENAME
    if not path.exists():
        raise LayoutDetectionError(f"No layout to describe: {path} does not exist")

    payload = json.loads(path.read_text(encoding="utf-8"))
    version = payload.get("version")
    if version != LAYOUT_FORMAT_VERSION:
        raise LayoutDetectionError(f"Unsupported layout format version {version!r} in {path}")

    elements = payload.get("elements") or []
    if not elements:
        raise LayoutDetectionError(f"Layout file {path} holds no elements")

    for element in elements:
        # JSON has no tuples, and centroid is one in memory. Restoring the type
        # keeps a described-from-disk report byte-identical to an in-memory one.
        if isinstance(element.get("centroid"), list):
            element["centroid"] = tuple(element["centroid"])

    pages_dir = directory / PAGES_DIRNAME
    page_paths = sorted(pages_dir.glob("page-*")) if pages_dir.is_dir() else []
    return elements, PageStore(page_paths, cache_size=cache_size)


def layout_exists(destination: str | Path) -> bool:
    return (Path(destination) / LAYOUT_FILENAME).exists()
