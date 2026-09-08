"""Run the structured paper parser over one or more PDFs, without a repository.

``python -m osa_tool.tools.paper_parsing.batch ./paper.pdf --output-dir out``
"""

from __future__ import annotations

import argparse
import os
from argparse import Namespace
from pathlib import Path

import dotenv

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.repository_validation.paper_parsing.models import PaperParsingOptions
from osa_tool.operations.analysis.repository_validation.paper_parsing.structured_parser import (
    DEFAULT_API_KEY_ENV,
    StructuredPaperParser,
)


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
    parser = argparse.ArgumentParser(description="Parse PDF papers into layout-aware markdown and a document graph.")
    parser.add_argument("pdfs", nargs="+", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("paper_parsing_results"))
    parser.add_argument("--config-file", default=None)
    parser.add_argument("--model", default=None, help="Vision-language model; overrides the configured vlm_model.")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible endpoint serving the VLM.")
    parser.add_argument(
        "--api-key-env",
        default=None,
        help=f"Environment variable holding the API key (default: configuration, else {DEFAULT_API_KEY_ENV}).",
    )
    parser.add_argument("--device", default=None, choices=["cpu", "cuda"])
    parser.add_argument("--conf-threshold", type=float, default=None)
    parser.add_argument("--max-concurrent", type=int, default=None)
    parser.add_argument("--downsample-factor", type=int, default=None)
    parser.add_argument(
        "--render-dpi",
        type=int,
        default=None,
        help="Page rasterization DPI (default 200). Lowering it cuts memory roughly quadratically.",
    )
    parser.add_argument("--layout-batch-size", type=int, default=None, help="Pages per layout-detection call.")
    parser.add_argument("--vlm-max-retries", type=int, default=None, help="Retries per element (default 3).")
    parser.add_argument("--vlm-retry-delay", type=float, default=None, help="Backoff base in seconds (default 2).")
    parser.add_argument("--vlm-timeout", type=float, default=None, help="Per-request timeout in seconds.")
    parser.add_argument("--save-img", action="store_true", help="Keep the rendered element crops on disk.")
    parser.add_argument("--include-report", action="store_true", help="Also export the raw layout report.")
    return parser


def build_options(args: Namespace, model_settings) -> PaperParsingOptions:
    """Layer the CLI overrides on top of the options read from the configuration."""
    values = StructuredPaperParser.options_from_model_settings(model_settings).model_dump()
    overrides = {
        "device": args.device,
        "conf_threshold": args.conf_threshold,
        "max_concurrent": args.max_concurrent,
        "downsample_factor": args.downsample_factor,
        "save_img": True if args.save_img else None,
        "render_dpi": args.render_dpi,
        "layout_batch_size": args.layout_batch_size,
        "vlm_max_retries": getattr(args, "vlm_max_retries", None),
        "vlm_retry_delay": getattr(args, "vlm_retry_delay", None),
        "vlm_timeout": getattr(args, "vlm_timeout", None),
    }
    values.update({key: value for key, value in overrides.items() if value is not None})
    return PaperParsingOptions(**values)


def main() -> int:
    args = build_parser().parse_args()
    pdfs, failures = collect_pdf_inputs(args.pdfs)
    if not pdfs:
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    dotenv.load_dotenv()
    config = ConfigManager(Namespace(config_file=args.config_file) if args.config_file else None)
    model_settings = config.get_model_settings("validation")
    options = build_options(args, model_settings)

    for pdf in pdfs:
        try:
            parser = StructuredPaperParser.from_model_settings(
                pdf,
                model_settings,
                vlm_model=args.model,
                vlm_base_url=args.base_url,
                api_key=os.getenv(args.api_key_env) if args.api_key_env else None,
                options=options,
            )
            result = parser.parse()
            parser.export(result, args.output_dir / pdf.stem, include_report=args.include_report)
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
