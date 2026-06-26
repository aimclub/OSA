from __future__ import annotations

import argparse
from pathlib import Path

from rich.progress import track

from osa_tool.operations.analysis.paper_claims.models import (
    MarkerOptions,
    PipelineOptions,
)
from osa_tool.operations.analysis.paper_claims.pipeline import PaperClaimPipeline
from osa_tool.utils.logger import logger, setup_logging


def collect_pdf_inputs(paths: list[Path]) -> tuple[list[Path], list[str]]:
    collected: set[Path] = set()
    failures: list[str] = []
    for raw_path in paths:
        path = raw_path.expanduser().resolve()
        if path.is_dir():
            pdfs = {item for item in path.iterdir() if item.is_file() and item.suffix.lower() == ".pdf"}
            if not pdfs:
                failures.append(f"{raw_path}: directory contains no PDF files")
            collected.update(pdfs)
        elif path.is_file() and path.suffix.lower() == ".pdf":
            collected.add(path)
        else:
            failures.append(f"{raw_path}: not a PDF file or directory")
    return sorted(collected), failures


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run claim extraction for multiple PDF documents.")
    parser.add_argument("pdfs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("paper_claim_results"))
    parser.add_argument("--repository", default="https://github.com/ai-chem/DiMag")
    parser.add_argument("--model", default="openai/gpt-5.4-mini")
    parser.add_argument("--config-file", default=None)
    parser.add_argument("--chunk-pages", type=int, default=10)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument(
        "--force-marker-refresh",
        action="store_true",
        help=(
            "Ignore existing cached Marker Markdown for this run and reconvert PDFs. "
            "Only Marker output is refreshed; LLM extraction still runs normally and is not cached."
        ),
    )
    parser.add_argument(
        "--marker-process-isolation",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Convert each PDF chunk in a separate Python process to release CUDA memory between chunks.",
    )
    parser.add_argument(
        "--marker-low-vram",
        action="store_true",
        help="Use conservative Marker batch sizes for low-VRAM GPUs.",
    )
    parser.add_argument(
        "--marker-log-cuda-memory",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Log CUDA memory before and after each Marker chunk when CUDA is available.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    setup_logging("paper_claims_batch", str(Path.cwd() / "logs"))
    logger.info("Paper claims batch started")
    pdfs, failures = collect_pdf_inputs(args.pdfs)
    if not pdfs:
        for failure in failures:
            logger.info("Input rejected: %s", failure)
        return 1
    logger.info("Collected %s PDF documents for processing", len(pdfs))
    # NOTE: heavy LLM imports inside main() so parser/help can load without importing the full LLM stack
    from osa_tool.config.settings import ConfigManager
    from osa_tool.core.llm.llm import ModelHandlerFactory

    config = ConfigManager(args)
    handler = ModelHandlerFactory.build(config.get_model_settings("validation"))
    pipeline = PaperClaimPipeline(handler)
    options = PipelineOptions(
        pages_per_chunk=args.chunk_pages,
        max_retries=args.max_retries,
        marker=MarkerOptions(
            force_refresh=args.force_marker_refresh,
            low_vram=args.marker_low_vram,
            process_isolation=args.marker_process_isolation,
            log_cuda_memory=args.marker_log_cuda_memory,
        ),
    )
    for pdf in track(pdfs, description="Processing PDF documents"):
        logger.info("Starting document %s", pdf)
        try:
            result = pipeline.run(pdf, options)
            output_path = pipeline.export(result, args.output_dir / pdf.stem, legacy=True)
            logger.info(
                "Document completed: %s; parsed_sections=%s; selected_sections=%s; final_claims=%s; output=%s",
                pdf,
                len(result.sections),
                len(result.extraction.selected_section_ids),
                len(result.extraction.claims),
                output_path,
            )
        except Exception as exc:
            failures.append(f"{pdf}: {exc}")
            logger.info("Document failed: %s; reason=%s", pdf, exc)
    if failures:
        logger.info("Paper claims batch completed with %s failures", len(failures))
        for failure in failures:
            logger.info("Failure: %s", failure)
        return 1
    logger.info("Paper claims batch completed successfully: %s documents", len(pdfs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
