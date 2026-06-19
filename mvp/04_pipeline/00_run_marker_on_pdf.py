#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_OUTPUT_DIR = "marker_output"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run marker-pdf (marker_single) on a PDF.")
    parser.add_argument("pdf", type=Path, help="Path to the input PDF file")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path(DEFAULT_OUTPUT_DIR),
        help=f"Directory for marker output (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--recognition-batch-size", type=int, default=6)
    parser.add_argument(
        "--enable-image-extraction",
        action="store_true",
        help="Enable image extraction. Disabled by default to reduce memory usage.",
    )
    return parser


def validate_input(pdf_path: Path) -> None:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    if not pdf_path.is_file():
        raise ValueError(f"Not a file: {pdf_path}")
    if pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Expected a .pdf file, got: {pdf_path.name}")


def resolve_marker_command() -> str:
    marker_cmd = shutil.which("marker_single")
    if marker_cmd:
        return marker_cmd
    raise RuntimeError("Could not find `marker_single` in PATH. Install marker-pdf first.")


def run_marker(pdf_path: Path, output_dir: Path, recognition_batch_size: int, disable_image_extraction: bool) -> int:
    marker_cmd = resolve_marker_command()
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [marker_cmd, str(pdf_path), "--output_dir", str(output_dir), "--recognition_batch_size", str(recognition_batch_size)]
    if disable_image_extraction:
        cmd.append("--disable_image_extraction")

    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode


def flatten_nested_output(pdf_path: Path, output_dir: Path) -> None:
    nested_dir = output_dir / pdf_path.stem
    if not nested_dir.exists() or not nested_dir.is_dir():
        return

    for child in nested_dir.iterdir():
        target = output_dir / child.name
        if target.exists():
            raise FileExistsError(f"Cannot flatten marker output, target already exists: {target}")
        shutil.move(str(child), str(target))

    nested_dir.rmdir()


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        pdf_path = args.pdf.expanduser().resolve()
        output_dir = args.output_dir.expanduser().resolve()

        validate_input(pdf_path)
        exit_code = run_marker(
            pdf_path,
            output_dir,
            recognition_batch_size=args.recognition_batch_size,
            disable_image_extraction=not args.enable_image_extraction,
        )
        if exit_code == 0:
            flatten_nested_output(pdf_path, output_dir)
            print(f"Done. Marker output written to: {output_dir}")
        else:
            print(f"marker_single exited with code {exit_code}")

        return exit_code

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
