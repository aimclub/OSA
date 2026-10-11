from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from rich.progress import track

from osa_tool.operations.analysis.paper_claims.exceptions import PdfConversionError
from osa_tool.operations.analysis.paper_claims.models import ConvertedChunk, ConvertedDocument, PdfChunk
from osa_tool.utils.logger import logger

DEFAULT_OPENROUTER_CACHE = Path(tempfile.gettempdir()) / "osa_tool" / "paper_claims" / "openrouter"


def _is_openrouter_url(base_url: str | None) -> bool:
    if not base_url:
        return False
    hostname = urlparse(base_url).hostname or ""
    return hostname == "openrouter.ai" or hostname.endswith(".openrouter.ai")


def extract_annotation_text(response: dict[str, Any]) -> str:
    """Read parsed PDF text from OpenRouter's chat-completion file annotations."""
    choices = response.get("choices")
    if not isinstance(choices, list):
        return ""

    text_blocks: list[str] = []
    for choice in choices:
        if not isinstance(choice, dict):
            continue
        message = choice.get("message")
        if not isinstance(message, dict):
            continue
        annotations = message.get("annotations")
        if not isinstance(annotations, list):
            continue
        for annotation in annotations:
            if not isinstance(annotation, dict) or annotation.get("type") != "file":
                continue
            file_data = annotation.get("file")
            content = file_data.get("content") if isinstance(file_data, dict) else None
            if not isinstance(content, list):
                continue
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    text = part.get("text")
                    if isinstance(text, str) and text.strip():
                        text_blocks.append(text.strip())
    return "\n\n".join(text_blocks).strip()


class OpenRouterDocumentConverter:
    """Convert PDF chunks through OpenRouter's Mistral OCR or Cloudflare parser."""

    def __init__(self, handler: Any, parser: str, cache_root: Path | None = None) -> None:
        if parser not in {"mistral-ocr", "cloudflare-ai"}:
            raise ValueError(f"Unsupported OpenRouter PDF parser: {parser}")
        base_url = getattr(getattr(handler, "model_settings", None), "base_url", None)
        if not _is_openrouter_url(base_url):
            raise PdfConversionError(
                f"The {parser} PDF parser requires an OpenRouter base URL; "
                f"configured base URL is {base_url!r}. Select Marker or configure OpenRouter for paper claims."
            )
        self.handler = handler
        self.parser = parser
        self.cache_root = Path(cache_root) if cache_root else DEFAULT_OPENROUTER_CACHE / parser

    @staticmethod
    def _validate_chunks(chunks: list[PdfChunk]) -> None:
        if not chunks:
            raise PdfConversionError("At least one PDF chunk is required")
        source_path = chunks[0].source_path
        source_hash = chunks[0].source_hash
        if any(chunk.source_path != source_path or chunk.source_hash != source_hash for chunk in chunks[1:]):
            raise PdfConversionError("All PDF chunks must originate from the same source_path and source_hash")

    def _cache_dir(self, chunks: list[PdfChunk]) -> Path:
        payload = {
            "source_hash": chunks[0].source_hash,
            "ranges": [(chunk.start_page, chunk.end_page) for chunk in chunks],
            "parser": self.parser,
        }
        key = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
        return self.cache_root / key

    def _load_cache(self, cache_dir: Path, chunks: list[PdfChunk]) -> ConvertedDocument | None:
        metadata_path = cache_dir / "metadata.json"
        merged_path = cache_dir / "merged.md"
        if not (cache_dir / "COMPLETE").is_file() or not metadata_path.is_file() or not merged_path.is_file():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("source_hash") != chunks[0].source_hash or metadata.get("parser") != self.parser:
                return None
            converted_chunks: list[ConvertedChunk] = []
            for chunk in sorted(chunks, key=lambda item: item.index):
                chunk_path = cache_dir / f"chunk_{chunk.index:04d}.md"
                markdown = chunk_path.read_text(encoding="utf-8")
                if not markdown.strip():
                    return None
                converted_chunks.append(
                    ConvertedChunk(
                        index=chunk.index,
                        start_page=chunk.start_page,
                        end_page=chunk.end_page,
                        markdown=markdown,
                        cache_path=chunk_path,
                    )
                )
            markdown = merged_path.read_text(encoding="utf-8")
            if not markdown.strip():
                return None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None
        return ConvertedDocument(
            source_path=chunks[0].source_path,
            source_hash=chunks[0].source_hash,
            chunks=converted_chunks,
            markdown=markdown,
            cache_hit=True,
            cache_dir=cache_dir,
            parser=self.parser,
        )

    async def convert(
        self,
        chunks: list[PdfChunk],
        *,
        force_refresh: bool = False,
        show_progress: bool = True,
    ) -> ConvertedDocument:
        self._validate_chunks(chunks)
        cache_dir = self._cache_dir(chunks)
        if force_refresh:
            shutil.rmtree(cache_dir, ignore_errors=True)
        else:
            cached = self._load_cache(cache_dir, chunks)
            if cached is not None:
                logger.info("Using cached %s output for %s chunks from %s", self.parser, len(chunks), cache_dir)
                return cached

        request_pdf = getattr(self.handler, "async_request_pdf", None)
        if not callable(request_pdf):
            raise PdfConversionError(
                "The configured LLM handler cannot send PDF parser requests. "
                "Use OSA's OpenRouter model handler for Mistral OCR or Cloudflare AI."
            )

        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "COMPLETE").unlink(missing_ok=True)
        converted_chunks: list[ConvertedChunk] = []
        ordered_chunks = sorted(chunks, key=lambda item: item.index)
        progress_items = (
            track(ordered_chunks, description=f"Parsing PDF chunks ({self.parser})")
            if show_progress
            else ordered_chunks
        )
        for chunk in progress_items:
            logger.info(
                "Parsing chunk %s/%s with %s: pages %s-%s",
                chunk.index,
                len(ordered_chunks),
                self.parser,
                chunk.start_page,
                chunk.end_page,
            )
            try:
                response = await request_pdf(chunk.path, parser=self.parser)
                markdown = extract_annotation_text(response)
            except Exception as exc:
                if isinstance(exc, PdfConversionError):
                    raise
                raise PdfConversionError(
                    f"OpenRouter {self.parser} parsing failed for pages " f"{chunk.start_page}-{chunk.end_page}: {exc}"
                ) from exc
            if not markdown:
                raise PdfConversionError(
                    f"OpenRouter {self.parser} returned no parsed text annotation "
                    f"for pages {chunk.start_page}-{chunk.end_page}"
                )

            markdown += "\n"
            cache_path = cache_dir / f"chunk_{chunk.index:04d}.md"
            cache_path.write_text(markdown, encoding="utf-8")
            converted_chunks.append(
                ConvertedChunk(
                    index=chunk.index,
                    start_page=chunk.start_page,
                    end_page=chunk.end_page,
                    markdown=markdown,
                    cache_path=cache_path,
                )
            )

        merged = "\n\n".join(item.markdown.strip() for item in converted_chunks).strip() + "\n"
        (cache_dir / "merged.md").write_text(merged, encoding="utf-8")
        (cache_dir / "metadata.json").write_text(
            json.dumps(
                {
                    "source": str(chunks[0].source_path),
                    "source_hash": chunks[0].source_hash,
                    "parser": self.parser,
                    "chunks": [
                        {"index": item.index, "start_page": item.start_page, "end_page": item.end_page}
                        for item in converted_chunks
                    ],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        (cache_dir / "COMPLETE").write_text("ok\n", encoding="utf-8")
        logger.info("OpenRouter parsing completed: %s chunks cached in %s", len(converted_chunks), cache_dir)
        return ConvertedDocument(
            source_path=chunks[0].source_path,
            source_hash=chunks[0].source_hash,
            chunks=converted_chunks,
            markdown=merged,
            cache_hit=False,
            cache_dir=cache_dir,
            parser=self.parser,
        )
