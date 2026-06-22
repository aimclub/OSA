from __future__ import annotations

import argparse
from pathlib import Path

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.operations.analysis.paper_claims.models import (
    MarkerOptions,
    PipelineOptions,
)
from osa_tool.operations.analysis.paper_claims.pipeline import PaperClaimPipeline


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
    # parser.add_argument("--repository", default="https://github.com/ai-chem/DiMag")
    parser.add_argument("--model", default=None)
    parser.add_argument("--config-file", default=None)
    parser.add_argument("--chunk-pages", type=int, default=10)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--force-marker-refresh", action="store_true")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    pdfs, failures = collect_pdf_inputs(args.pdfs)
    if not pdfs:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1
    config = ConfigManager(args)
    handler = ModelHandlerFactory.build(config.get_model_settings("validation"))
    pipeline = PaperClaimPipeline(handler)
    options = PipelineOptions(
        pages_per_chunk=args.chunk_pages,
        max_retries=args.max_retries,
        marker=MarkerOptions(force_refresh=args.force_marker_refresh),
    )
    for pdf in pdfs:
        try:
            result = pipeline.run(pdf, options)
            pipeline.export(result, args.output_dir / pdf.stem, legacy=True)
            print(f"OK: {pdf}")
        except Exception as exc:
            failures.append(f"{pdf}: {exc}")
            print(f"ERROR: {pdf}: {exc}")
    if failures:
        print("Failures:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
