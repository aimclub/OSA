#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DEFAULT_DATA_ROOT = Path("/home/ilya/Desktop/06_multi_doc_data")
DEFAULT_REPOSITORY = "https://github.com/ai-chem/DiMag"
DEFAULT_MODEL = "deepseek/deepseek-v4-flash"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-run claim extraction only for documents with empty result arrays.")
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DEFAULT_DATA_ROOT,
        help="Root directory that contains sheet_* subdirectories.",
    )
    parser.add_argument("--repository", default=DEFAULT_REPOSITORY)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-retries", type=int, default=10)
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--config-file", default=None, help="Optional path to OSA config.toml")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only print what would be rerun, without executing claim extraction.",
    )
    return parser.parse_args()


def is_empty_result(claims_json_path: Path) -> tuple[bool, str]:
    try:
        payload = json.loads(claims_json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return True, f"invalid json ({exc})"

    result = payload.get("result")
    if isinstance(result, list) and len(result) == 0:
        return True, "result is empty"
    if isinstance(result, list) and len(result) > 0:
        return False, "result is non-empty"
    return True, "missing or invalid result field"


def run_cmd(cmd: list[str]) -> int:
    print("Running:", " ".join(cmd))
    completed = subprocess.run(cmd, check=False)
    return completed.returncode


def main() -> int:
    args = parse_args()
    data_root = args.data_root.expanduser().resolve()

    if not data_root.exists() or not data_root.is_dir():
        print(f"Data root is not a directory: {data_root}")
        return 1

    pipeline_dir = Path(__file__).resolve().parent
    extract_script = pipeline_dir / "02_claim_extraction_mvp.py"
    if not extract_script.exists():
        print(f"Cannot find extraction script: {extract_script}")
        return 1

    candidates = sorted(p for p in data_root.iterdir() if p.is_dir() and p.name.startswith("sheet_"))
    if not candidates:
        print(f"No sheet_* directories found under: {data_root}")
        return 1

    checked = 0
    skipped = 0
    to_rerun = 0
    rerun_ok = 0
    rerun_failed = 0
    problems: list[tuple[str, str]] = []

    for doc_dir in candidates:
        checked += 1
        doc_id = doc_dir.name
        claims_path = doc_dir / f"{doc_id}_claims_result.json"
        sections_path = doc_dir / f"{doc_id}_sections_v3.json"

        if not claims_path.exists():
            problems.append((str(doc_dir), f"claims file missing: {claims_path.name}"))
            skipped += 1
            continue
        if not sections_path.exists():
            problems.append((str(doc_dir), f"sections file missing: {sections_path.name}"))
            skipped += 1
            continue

        empty, reason = is_empty_result(claims_path)
        if not empty:
            print(f"Skip {doc_id}: {reason}")
            skipped += 1
            continue

        to_rerun += 1
        print(f"Rerun {doc_id}: {reason}")

        if args.dry_run:
            continue

        cmd = [
            sys.executable,
            str(extract_script),
            "--attachment",
            str(sections_path),
            "--repository",
            args.repository,
            "--model",
            args.model,
            "--max-retries",
            str(args.max_retries),
            "--log-level",
            args.log_level,
            "--output",
            str(claims_path),
        ]
        if args.config_file:
            cmd.extend(["--config-file", str(Path(args.config_file).expanduser().resolve())])

        rc = run_cmd(cmd)
        if rc == 0:
            empty, reason = is_empty_result(claims_path)
            if not empty:
                rerun_ok += 1
            else:
                rerun_failed += 1
                problems.append((str(doc_dir), f"claim extraction failed with code {reason}"))
        else:
            rerun_failed += 1
            problems.append((str(doc_dir), f"claim extraction failed with code {rc}"))

        print("\nSummary:")
        print(f"- checked: {checked}")
        print(f"- skipped: {skipped}")
        print(f"- to_rerun: {to_rerun}")
        print(f"- rerun_ok: {rerun_ok}")
        print(f"- rerun_failed: {rerun_failed}")

    if problems:
        print("\nProblems:")
        for path, message in problems:
            print(f"- {path}: {message}")

    if rerun_failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
