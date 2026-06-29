from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


def aggregate_evaluations(paths: Iterable[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted({Path(item).resolve() for item in paths}):
        payload = json.loads(path.read_text(encoding="utf-8"))
        metrics = payload.get("semantic_matching", payload)
        rows.append({"paper": path.parent.name, **metrics})
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate claim-evaluation JSON files into CSV.")
    parser.add_argument("inputs", nargs="+", type=Path, help="Evaluation JSON files or directories")
    parser.add_argument("--pattern", default="**/*evaluation*.json")
    parser.add_argument("--output", type=Path, default=Path("aggregated_claims_metrics.csv"))
    args = parser.parse_args()
    paths: list[Path] = []
    for item in args.inputs:
        paths.extend(item.glob(args.pattern) if item.is_dir() else [item])
    rows = aggregate_evaluations(path for path in paths if path.is_file())
    if not rows:
        parser.error("No evaluation JSON files found")
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError(
            "Aggregation dependencies are missing; install the project dependencies from pyproject.toml "
            "or requirements.txt."
        ) from exc
    frame = pd.DataFrame(rows).sort_values("paper").reset_index(drop=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(args.output, index=False)
    print(frame.to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
