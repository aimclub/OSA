from __future__ import annotations

import argparse
import gc
import hashlib
import importlib.metadata
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from rich.progress import track

from osa_tool.operations.analysis.paper_claims.exceptions import PdfConversionError
from osa_tool.operations.analysis.paper_claims.models import ConvertedChunk, ConvertedDocument, MarkerOptions, PdfChunk
from osa_tool.utils.logger import logger

DEFAULT_MARKER_CACHE = Path(tempfile.gettempdir()) / "osa_tool" / "paper_claims" / "marker"
LOW_VRAM_MARKER_CONFIG = {
    "layout_batch_size": 1,
    "detection_batch_size": 1,
    "ocr_error_batch_size": 1,
    "recognition_batch_size": 8,
    "table_rec_batch_size": 4,
    "equation_batch_size": 4,
}


def clear_marker_cache(cache_root: Path | None = None) -> None:
    """Delete all cached Marker output under *cache_root*."""
    shutil.rmtree(Path(cache_root) if cache_root else DEFAULT_MARKER_CACHE, ignore_errors=True)


def _effective_marker_config(options: MarkerOptions) -> dict[str, Any]:
    config: dict[str, Any] = {}
    if options.low_vram:
        config.update(LOW_VRAM_MARKER_CONFIG)
    config.update(options.marker_config)
    return config


def _load_torch() -> Any | None:
    try:
        import torch
    except ImportError:
        return None
    return torch


def _cuda_is_available(torch: Any | None) -> bool:
    if torch is None:
        return False
    try:
        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _cuda_memory_snapshot(torch: Any | None) -> str | None:
    if not _cuda_is_available(torch):
        return None
    allocated_mb = torch.cuda.memory_allocated() / 1024 / 1024
    reserved_mb = torch.cuda.memory_reserved() / 1024 / 1024
    peak_reserved_mb = torch.cuda.max_memory_reserved() / 1024 / 1024
    return f"allocated={allocated_mb:.0f} MiB reserved={reserved_mb:.0f} MiB peak_reserved={peak_reserved_mb:.0f} MiB"


def _log_cuda_memory(message: str, *, options: MarkerOptions, torch: Any | None) -> None:
    if not options.log_cuda_memory:
        return
    snapshot = _cuda_memory_snapshot(torch)
    if snapshot:
        logger.info("%s: %s", message, snapshot)


def _cleanup_marker_chunk_memory(*, torch: Any | None) -> None:
    gc.collect()
    if _cuda_is_available(torch):
        torch.cuda.empty_cache()


def _render_chunk_markdown(
    converter: Any,
    render_text: Callable[[Any], str],
    chunk_path: Path,
    options: MarkerOptions,
) -> str:
    torch = _load_torch()
    rendered = None
    try:
        if torch is not None:
            with torch.inference_mode():
                rendered = converter(str(chunk_path))
        else:
            rendered = converter(str(chunk_path))
        return render_text(rendered).strip()
    finally:
        rendered = None
        _cleanup_marker_chunk_memory(torch=torch)


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
        **_effective_marker_config(options),
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
        self._uses_default_factory = converter_factory is None
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
            "marker_config": _effective_marker_config(options),
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

    def _convert_chunk_with_reused_converter(
        self,
        *,
        converter: Any,
        render_text: Callable[[Any], str],
        chunk: PdfChunk,
        chunk_count: int,
        options: MarkerOptions,
    ) -> str:
        torch = _load_torch()
        _log_cuda_memory(
            f"CUDA memory before Marker chunk {chunk.index}/{chunk_count}",
            options=options,
            torch=torch,
        )
        if _cuda_is_available(torch) and options.log_cuda_memory:
            torch.cuda.reset_peak_memory_stats()
        started_at = time.perf_counter()
        markdown = _render_chunk_markdown(converter, render_text, chunk.path, options)
        elapsed = time.perf_counter() - started_at
        _log_cuda_memory(
            f"CUDA memory after Marker chunk {chunk.index}/{chunk_count}",
            options=options,
            torch=torch,
        )
        logger.info(
            "Marker chunk %s/%s rendered in %.1fs",
            chunk.index,
            chunk_count,
            elapsed,
        )
        return markdown

    def _convert_chunk_in_subprocess(
        self,
        *,
        chunk: PdfChunk,
        chunk_count: int,
        options: MarkerOptions,
        output_path: Path,
    ) -> str:
        payload_path = output_path.with_suffix(".json")
        payload = {
            "pdf_path": str(chunk.path),
            "output_path": str(output_path),
            "options": {
                "extract_images": options.extract_images,
                "low_vram": options.low_vram,
                "log_cuda_memory": options.log_cuda_memory,
                "marker_config": options.marker_config,
            },
        }
        payload_path.write_text(json.dumps(payload, ensure_ascii=False, default=str), encoding="utf-8")
        logger.info(
            "Starting isolated Marker worker for chunk %s/%s: pages %s-%s",
            chunk.index,
            chunk_count,
            chunk.start_page,
            chunk.end_page,
        )
        started_at = time.perf_counter()
        try:
            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "osa_tool.operations.analysis.paper_claims.marker_converter",
                    "--worker-payload",
                    str(payload_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        finally:
            payload_path.unlink(missing_ok=True)
        elapsed = time.perf_counter() - started_at
        if completed.stdout.strip():
            logger.debug("Isolated Marker worker stdout for chunk %s: %s", chunk.index, completed.stdout.strip())
        if completed.stderr.strip():
            logger.debug("Isolated Marker worker stderr for chunk %s: %s", chunk.index, completed.stderr.strip())
        if completed.returncode != 0:
            error = completed.stderr.strip() or completed.stdout.strip() or "no worker output"
            raise PdfConversionError(
                f"Isolated Marker worker failed for pages {chunk.start_page}-{chunk.end_page}: {error[-4000:]}"
            )
        try:
            markdown = output_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise PdfConversionError(f"Isolated Marker worker did not write output for chunk {chunk.index}") from exc
        logger.info("Isolated Marker worker completed chunk %s/%s in %.1fs", chunk.index, chunk_count, elapsed)
        return markdown

    def _convert_chunk(
        self,
        *,
        converter: Any | None,
        render_text: Callable[[Any], str] | None,
        chunk: PdfChunk,
        chunk_count: int,
        options: MarkerOptions,
        cache_path: Path,
    ) -> str:
        if options.process_isolation:
            return self._convert_chunk_in_subprocess(
                chunk=chunk,
                chunk_count=chunk_count,
                options=options,
                output_path=cache_path,
            )
        if converter is None or render_text is None:
            raise PdfConversionError("Marker converter was not initialized")
        return self._convert_chunk_with_reused_converter(
            converter=converter,
            render_text=render_text,
            chunk=chunk,
            chunk_count=chunk_count,
            options=options,
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
                logger.info("Using cached Marker output for %s chunks from %s", len(chunks), cache_dir)
                return cached

        effective_config = _effective_marker_config(options)
        if options.low_vram:
            logger.info("Using low-VRAM Marker settings: %s", effective_config)
        if options.process_isolation:
            if not self._uses_default_factory:
                raise PdfConversionError("Marker process isolation requires the default Marker converter factory")
            logger.info("Using isolated Marker worker processes for %s chunks", len(chunks))
            converter = None
            render_text = None
            marker_version = self.marker_version
        else:
            logger.info("Initializing Marker converter for %s chunks", len(chunks))
            converter, render_text, marker_version = self.converter_factory(options)

        if options.force_refresh:
            shutil.rmtree(cache_dir, ignore_errors=True)
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "COMPLETE").unlink(missing_ok=True)

        converted_chunks: list[ConvertedChunk] = []
        try:
            ordered_chunks = sorted(chunks, key=lambda item: item.index)
            for chunk in track(ordered_chunks, description="Converting PDF chunks"):
                logger.info(
                    "Converting chunk %s/%s with Marker: pages %s-%s",
                    chunk.index,
                    len(ordered_chunks),
                    chunk.start_page,
                    chunk.end_page,
                )
                cache_path = cache_dir / f"chunk_{chunk.index:04d}.md"
                markdown = self._convert_chunk(
                    converter=converter,
                    render_text=render_text,
                    chunk=chunk,
                    chunk_count=len(ordered_chunks),
                    options=options,
                    cache_path=cache_path,
                )
                if not markdown:
                    raise PdfConversionError(
                        f"Marker produced empty output for pages {chunk.start_page}-{chunk.end_page}"
                    )
                markdown += "\n"
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
                logger.info(
                    "Marker chunk %s/%s completed: pages %s-%s",
                    chunk.index,
                    len(ordered_chunks),
                    chunk.start_page,
                    chunk.end_page,
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
            "marker_config": effective_config,
            "process_isolation": options.process_isolation,
            "chunks": [
                {"index": item.index, "start_page": item.start_page, "end_page": item.end_page}
                for item in converted_chunks
            ],
        }
        (cache_dir / "metadata.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        (cache_dir / "COMPLETE").write_text("ok\n", encoding="utf-8")
        logger.info("Marker conversion completed: %s chunks cached in %s", len(converted_chunks), cache_dir)
        return ConvertedDocument(
            source_path=chunks[0].source_path,
            source_hash=chunks[0].source_hash,
            chunks=converted_chunks,
            markdown=merged,
            cache_hit=False,
            cache_dir=cache_dir,
        )


def _worker_payload_to_options(raw_options: dict[str, Any]) -> MarkerOptions:
    return MarkerOptions(
        extract_images=bool(raw_options.get("extract_images", False)),
        low_vram=bool(raw_options.get("low_vram", False)),
        log_cuda_memory=bool(raw_options.get("log_cuda_memory", True)),
        marker_config=dict(raw_options.get("marker_config", {})),
    )


def _run_marker_worker(payload_path: Path) -> int:
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        options = _worker_payload_to_options(payload.get("options", {}))
        converter, render_text, _marker_version = _default_converter_factory(options)
        markdown = _render_chunk_markdown(converter, render_text, Path(payload["pdf_path"]), options)
        if not markdown:
            raise PdfConversionError("Marker produced empty output")
        Path(payload["output_path"]).write_text(markdown + "\n", encoding="utf-8")
        converter = None
        _cleanup_marker_chunk_memory(torch=_load_torch())
        return 0
    except Exception as exc:
        logger.exception("Isolated Marker worker failed: %s", exc)
        return 1


def _build_worker_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Internal Marker chunk worker.")
    parser.add_argument("--worker-payload", type=Path, required=True)
    return parser


if __name__ == "__main__":
    worker_args = _build_worker_parser().parse_args()
    raise SystemExit(_run_marker_worker(worker_args.worker_payload))
