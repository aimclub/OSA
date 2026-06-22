from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

from rich.progress import track

from osa_tool.operations.analysis.paper_claims.exceptions import PdfConversionError, PdfInputError
from osa_tool.operations.analysis.paper_claims.models import PdfChunk
from osa_tool.utils.logger import logger


def hash_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


class PdfChunker:
    """Split one PDF into physical files and own their temporary directory."""

    def __init__(self, work_dir: Path | None = None) -> None:
        self._owned_work_dir = work_dir is None
        self.work_dir = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="osa-paper-chunks-"))

    @staticmethod
    def validate(pdf_path: Path) -> Path:
        path = Path(pdf_path).expanduser().resolve()
        if not path.exists():
            raise PdfInputError(f"PDF not found: {path}")
        if not path.is_file():
            raise PdfInputError(f"PDF path is not a file: {path}")
        if path.suffix.lower() != ".pdf":
            raise PdfInputError(f"Expected a .pdf file: {path}")
        with path.open("rb") as source:
            if source.read(5) != b"%PDF-":
                raise PdfInputError(f"File does not have a PDF signature: {path}")
        return path

    def split(self, pdf_path: Path, pages_per_chunk: int = 10) -> list[PdfChunk]:
        if pages_per_chunk <= 0:
            raise ValueError("pages_per_chunk must be greater than zero")
        path = self.validate(pdf_path)
        try:
            from pypdf import PdfReader, PdfWriter
        except ImportError as exc:
            raise PdfConversionError("PDF splitting requires `pypdf`. Install the paper-claims dependencies.") from exc

        try:
            reader = PdfReader(str(path))
            page_count = len(reader.pages)
        except Exception as exc:
            raise PdfConversionError(f"Cannot read PDF {path}: {exc}") from exc
        if page_count == 0:
            raise PdfInputError(f"PDF contains no pages: {path}")

        logger.info(
            "Splitting PDF '%s': %s pages, %s pages per chunk",
            path.name,
            page_count,
            pages_per_chunk,
        )
        self.work_dir.mkdir(parents=True, exist_ok=True)
        source_hash = hash_file(path)
        chunks: list[PdfChunk] = []
        chunk_starts = range(0, page_count, pages_per_chunk)
        for index, start in enumerate(track(chunk_starts, description="Splitting PDF"), start=1):
            end = min(start + pages_per_chunk, page_count)
            chunk_path = self.work_dir / f"{path.stem}__p{start + 1:04d}-{end:04d}.pdf"
            writer = PdfWriter()
            for page_index in range(start, end):
                writer.add_page(reader.pages[page_index])
            try:
                with chunk_path.open("wb") as output:
                    writer.write(output)
            except Exception as exc:
                raise PdfConversionError(f"Failed to write PDF chunk {chunk_path}: {exc}") from exc
            chunks.append(
                PdfChunk(
                    path=chunk_path,
                    index=index,
                    start_page=start + 1,
                    end_page=end,
                    source_path=path,
                    source_hash=source_hash,
                )
            )
            logger.info("Created PDF chunk %s: pages %s-%s", index, start + 1, end)
        logger.info("PDF splitting completed: %s chunks created", len(chunks))
        return chunks

    def cleanup(self) -> None:
        if self._owned_work_dir:
            shutil.rmtree(self.work_dir, ignore_errors=True)

    def __enter__(self) -> "PdfChunker":
        return self

    def __exit__(self, *_: object) -> None:
        self.cleanup()
