#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter

DEFAULT_MARKER_OUTPUT_ROOT = Path("mvp/06_multi_doc_data")
DEFAULT_RESULTS_ROOT = Path("mvp/06_multi_doc_data")
DEFAULT_REPOSITORY = "https://github.com/ai-chem/DiMag"
DEFAULT_MODEL = "openai/gpt-oss-120b"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run multi-doc pipeline: marker -> sections -> claims extraction."
    )
    parser.add_argument(
        "pdfs",
        nargs="+",
        type=Path,
        help="Input PDF files and/or directories containing PDF files",
    )
    parser.add_argument("--marker-output-root", type=Path, default=DEFAULT_MARKER_OUTPUT_ROOT)
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-retries", type=int, default=5)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--chunk-pages", type=int, default=0, help="Pages per chunk. Use 0 to disable chunking.")
    parser.add_argument(
        "--delete-chunks",
        action="store_true",
        help="Delete generated chunk PDFs and per-chunk marker outputs after run. By default they are kept.",
    )
    return parser.parse_args()


def run_cmd(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def collect_pdf_inputs(paths: list[Path]) -> tuple[list[Path], list[tuple[str, str]]]:
    collected: list[Path] = []
    failures: list[tuple[str, str]] = []

    for p in paths:
        resolved = p.expanduser().resolve()
        if not resolved.exists():
            failures.append((str(p), "path does not exist"))
            continue

        if resolved.is_dir():
            dir_pdfs = sorted(x for x in resolved.iterdir() if x.is_file() and x.suffix.lower() == ".pdf")
            if not dir_pdfs:
                failures.append((str(p), "directory contains no pdf files"))
                continue
            collected.extend(dir_pdfs)
            continue

        if resolved.is_file() and resolved.suffix.lower() == ".pdf":
            collected.append(resolved)
            continue

        failures.append((str(p), "not a pdf file or directory"))

    unique_sorted = sorted(set(collected))
    return unique_sorted, failures


def split_pdf_into_chunks(pdf_path: Path, chunk_pages: int, chunk_dir: Path) -> list[tuple[Path, int, int]]:
    reader = PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    if total_pages == 0:
        return []

    chunk_dir.mkdir(parents=True, exist_ok=True)
    chunks: list[tuple[Path, int, int]] = []

    for start in range(0, total_pages, chunk_pages):
        end = min(start + chunk_pages, total_pages)
        writer = PdfWriter()
        for page_idx in range(start, end):
            writer.add_page(reader.pages[page_idx])

        start_1 = start + 1
        end_1 = end
        chunk_name = f"{pdf_path.stem}__p{start_1:03d}-{end_1:03d}.pdf"
        chunk_path = chunk_dir / chunk_name
        with chunk_path.open("wb") as f:
            writer.write(f)

        chunks.append((chunk_path, start_1, end_1))

    return chunks


def find_markdown_in_dir(output_dir: Path, stem: str) -> Path | None:
    direct = output_dir / f"{stem}.md"
    if direct.exists():
        return direct

    exact = sorted(output_dir.rglob(f"{stem}.md"))
    if exact:
        return exact[0]

    any_md = sorted(output_dir.rglob("*.md"))
    if any_md:
        return any_md[0]

    return None


def merge_markdowns(markdown_inputs: list[tuple[Path, int, int]], output_path: Path) -> Path:
    parts: list[str] = []
    for md_path, start_page, end_page in markdown_inputs:
        text = md_path.read_text(encoding="utf-8")
        body = text.strip()
        if not body:
            continue
        parts.append(f"<!-- chunk:{start_page}-{end_page} source:{md_path.name} -->\n\n{body}")

    merged = "\n\n---\n\n".join(parts).strip() + "\n"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(merged, encoding="utf-8")
    return output_path


def main() -> int:
    args = parse_args()

    pipeline_dir = Path(__file__).resolve().parent
    marker_script = pipeline_dir / "00_run_marker_on_pdf.py"
    sections_script = pipeline_dir / "01_parse_pdf_with_marker.py"
    extract_script = pipeline_dir / "02_claim_extraction_mvp.py"

    marker_root = args.marker_output_root.expanduser().resolve()
    results_root = args.results_root.expanduser().resolve()
    marker_root.mkdir(parents=True, exist_ok=True)
    results_root.mkdir(parents=True, exist_ok=True)

    input_pdfs, failed = collect_pdf_inputs(args.pdfs)
    if not input_pdfs:
        print("No valid PDF inputs found.")
        if failed:
            print("\nInput errors:")
            for path, reason in failed:
                print(f"- {path}: {reason}")
        return 1

    for pdf_path in input_pdfs:

        doc_id = pdf_path.stem
        doc_dir = results_root / doc_id
        chunks_pdf_dir = doc_dir / "chunks" / "pdfs"
        chunks_marker_dir = doc_dir / "chunks" / "marker"
        doc_marker_dir = marker_root / doc_id
        doc_dir.mkdir(parents=True, exist_ok=True)
        chunks_marker_dir.mkdir(parents=True, exist_ok=True)
        doc_marker_dir.mkdir(parents=True, exist_ok=True)

        try:
            if args.chunk_pages > 0:
                chunks = split_pdf_into_chunks(pdf_path, args.chunk_pages, chunks_pdf_dir)
                if not chunks:
                    failed.append((str(pdf_path), "pdf split produced no chunks"))
                    continue
            else:
                chunks = [(pdf_path, 1, 0)]
        except Exception as exc:
            failed.append((str(pdf_path), f"pdf split failed: {exc}"))
            continue

        chunk_markdowns: list[tuple[Path, int, int]] = []
        chunk_failures: list[str] = []

        for chunk_pdf, start_page, end_page in chunks:
            chunk_id = chunk_pdf.stem
            chunk_marker_out = chunks_marker_dir / chunk_id if args.chunk_pages > 0 else doc_marker_dir / chunk_id

            marker_cmd = [
                sys.executable,
                str(marker_script),
                str(chunk_pdf),
                "--output-dir",
                str(chunk_marker_out),
            ]
            marker_rc = run_cmd(marker_cmd)
            if marker_rc != 0:
                chunk_failures.append(f"{chunk_id}: marker failed with code {marker_rc}")
                continue

            markdown_path = find_markdown_in_dir(chunk_marker_out, chunk_id)
            if markdown_path is None:
                chunk_failures.append(f"{chunk_id}: markdown not found under {chunk_marker_out}")
                continue

            chunk_markdowns.append((markdown_path, start_page, end_page))

        if not chunk_markdowns:
            failed.append((str(pdf_path), "all chunks failed before markdown merge"))
            continue

        chunk_markdowns.sort(key=lambda item: item[1])
        merged_markdown_path = doc_dir / f"{doc_id}.md"

        try:
            merge_markdowns(chunk_markdowns, merged_markdown_path)
        except Exception as exc:
            failed.append((str(pdf_path), f"markdown merge failed: {exc}"))
            continue

        sections_json = doc_dir / f"{doc_id}_sections_v3.json"
        prepare_cmd = [
            sys.executable,
            str(sections_script),
            str(merged_markdown_path),
            "--output",
            str(sections_json),
        ]
        prepare_rc = run_cmd(prepare_cmd)
        if prepare_rc != 0:
            failed.append((str(pdf_path), f"section preparation failed with code {prepare_rc}"))
            continue

        try:
            prepared = json.loads(sections_json.read_text(encoding="utf-8"))
            if not isinstance(prepared, list) or len(prepared) == 0:
                failed.append((str(pdf_path), f"prepared sections are empty: {sections_json}"))
                continue
        except Exception as exc:
            failed.append((str(pdf_path), f"cannot validate sections json: {exc}"))
            continue

        claims_output = doc_dir / f"{doc_id}_claims_result.json"
        extract_cmd = [
            sys.executable,
            str(extract_script),
            "--attachment",
            str(sections_json),
            "--repository",
            args.repository,
            "--model",
            args.model,
            "--max-retries",
            str(args.max_retries),
            "--log-level",
            args.log_level,
            "--output",
            str(claims_output),
        ]
        extract_rc = run_cmd(extract_cmd)
        if extract_rc != 0:
            failed.append((str(pdf_path), f"claim extraction failed with code {extract_rc}"))
            continue

        if args.chunk_pages > 0 and args.delete_chunks:
            for chunk_pdf, _, _ in chunks:
                if chunk_pdf.exists() and chunk_pdf.parent == chunks_pdf_dir:
                    try:
                        chunk_pdf.unlink()
                    except OSError:
                        pass

        print(f"Done document: {pdf_path} -> {claims_output}")

        if chunk_failures:
            failed.append((str(pdf_path), "partial chunk failures: " + "; ".join(chunk_failures)))

    if failed:
        print("\nSome documents failed:")
        for path, reason in failed:
            print(f"- {path}: {reason}")
        return 1

    print("\nAll documents processed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
