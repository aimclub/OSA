from __future__ import annotations

import hashlib
import importlib.metadata
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any, Callable

from osa_tool.operations.analysis.paper_claims.exceptions import PdfConversionError
from osa_tool.operations.analysis.paper_claims.models import ConvertedChunk, ConvertedDocument, MarkerOptions, PdfChunk

DEFAULT_MARKER_CACHE = Path(tempfile.gettempdir()) / "osa_tool" / "paper_claims" / "marker"


def clear_marker_cache(cache_root: Path | None = None) -> None:
    """Delete all cached Marker output under *cache_root*."""
    shutil.rmtree(Path(cache_root) if cache_root else DEFAULT_MARKER_CACHE, ignore_errors=True)


def _default_converter_factory(options: MarkerOptions) -> tuple[Any, Callable[[Any], str], str]:
    try:
        from marker.config.parser import ConfigParser
        from marker.converters.pdf import PdfConverter
        from marker.models import create_model_dict
        from marker.output import text_from_rendered
    except ImportError as exc:
        raise PdfConversionError(
            "Marker conversion requires `marker-pdf` in the active environment. The current Marker release "
            "conflicts with ProtoLLM's OpenAI dependency, so OSA cannot declare it as an install extra; "
            "provision Marker separately with compatible dependencies."
        ) from exc

    config_values = {
        "output_format": "markdown",
        "disable_image_extraction": not options.extract_images,
        **options.marker_config,
    }
    parser = ConfigParser(config_values)
    converter = PdfConverter(
        artifact_dict=create_model_dict(),
        config=parser.generate_config_dict(),
        processor_list=parser.get_processors(),
        renderer=parser.get_renderer(),
        llm_service=parser.get_llm_service(),
    )

    def render_text(rendered: Any) -> str:
        markdown = getattr(rendered, "markdown", None)
        if isinstance(markdown, str):
            return markdown
        text, _, _ = text_from_rendered(rendered)
        return str(text)

    try:
        version = importlib.metadata.version("marker-pdf")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    return converter, render_text, version


class MarkerDocumentConverter:
    """Convert physical PDF chunks with one Marker converter instance."""

    def __init__(
        self,
        converter_factory: Callable[[MarkerOptions], tuple[Any, Callable[[Any], str], str]] | None = None,
        marker_version: str | None = None,
    ) -> None:
        self.converter_factory = converter_factory or _default_converter_factory
        if marker_version is not None:
            self.marker_version = marker_version
        else:
            try:
                self.marker_version = importlib.metadata.version("marker-pdf")
            except importlib.metadata.PackageNotFoundError:
                self.marker_version = "unknown"

    @staticmethod
    def _cache_key(chunks: list[PdfChunk], options: MarkerOptions, marker_version: str) -> str:
        payload = {
            "source_hash": chunks[0].source_hash,
            "ranges": [(chunk.start_page, chunk.end_page) for chunk in chunks],
            "marker_version": marker_version,
            "extract_images": options.extract_images,
            "marker_config": options.marker_config,
        }
        serialized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    @staticmethod
    def _load_cache(cache_dir: Path, chunks: list[PdfChunk]) -> ConvertedDocument | None:
        metadata_path = cache_dir / "metadata.json"
        merged_path = cache_dir / "merged.md"
        if not (cache_dir / "COMPLETE").is_file() or not metadata_path.is_file() or not merged_path.is_file():
            return None
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            if metadata.get("source_hash") != chunks[0].source_hash:
                return None
            converted_chunks: list[ConvertedChunk] = []
            for chunk in chunks:
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
            merged = merged_path.read_text(encoding="utf-8")
            if not merged.strip():
                return None
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return None
        return ConvertedDocument(
            source_path=chunks[0].source_path,
            source_hash=chunks[0].source_hash,
            chunks=converted_chunks,
            markdown=merged,
            cache_hit=True,
            cache_dir=cache_dir,
        )

    def convert(self, chunks: list[PdfChunk], options: MarkerOptions | None = None) -> ConvertedDocument:
        if not chunks:
            raise PdfConversionError("At least one PDF chunk is required")
        options = options or MarkerOptions()
        cache_root = options.cache_root or DEFAULT_MARKER_CACHE
        cache_dir = Path(cache_root) / self._cache_key(chunks, options, self.marker_version)
        if not options.force_refresh:
            cached = self._load_cache(cache_dir, chunks)
            if cached is not None:
                return cached

        converter, render_text, marker_version = self.converter_factory(options)

        if options.force_refresh:
            shutil.rmtree(cache_dir, ignore_errors=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "COMPLETE").unlink(missing_ok=True)

        converted_chunks: list[ConvertedChunk] = []
        try:
            for chunk in sorted(chunks, key=lambda item: item.index):
                markdown = render_text(converter(str(chunk.path))).strip()
                if not markdown:
                    raise PdfConversionError(
                        f"Marker produced empty output for pages {chunk.start_page}-{chunk.end_page}"
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
        except PdfConversionError:
            raise
        except Exception as exc:
            raise PdfConversionError(f"Marker conversion failed: {exc}") from exc

        merged = "\n\n".join(item.markdown.strip() for item in converted_chunks).strip() + "\n"
        (cache_dir / "merged.md").write_text(merged, encoding="utf-8")
        metadata = {
            "source": str(chunks[0].source_path),
            "source_hash": chunks[0].source_hash,
            "marker_version": marker_version,
            "extract_images": options.extract_images,
            "marker_config": options.marker_config,
            "chunks": [
                {"index": item.index, "start_page": item.start_page, "end_page": item.end_page}
                for item in converted_chunks
            ],
        }
        (cache_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        (cache_dir / "COMPLETE").write_text("ok\n", encoding="utf-8")
        return ConvertedDocument(
            source_path=chunks[0].source_path,
            source_hash=chunks[0].source_hash,
            chunks=converted_chunks,
            markdown=merged,
            cache_hit=False,
            cache_dir=cache_dir,
        )
