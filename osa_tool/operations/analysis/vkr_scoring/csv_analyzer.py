"""
Lightweight CSV analysis for claim verification.

Extracts row count, column names, dtypes, missing-value stats, and
unique-value counts from raw CSV text — no pandas required.
"""
from __future__ import annotations

import csv
import io
import math
from typing import Any


def _infer_type(values: list[str]) -> str:
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "empty"
    numeric = 0
    for v in non_empty:
        try:
            float(v.replace(",", "."))
            numeric += 1
        except ValueError:
            pass
    return "numeric" if numeric / len(non_empty) >= 0.8 else "categorical"


def _numeric_stats(values: list[str]) -> dict[str, Any]:
    nums = []
    for v in values:
        v = v.strip()
        if not v:
            continue
        try:
            nums.append(float(v.replace(",", ".")))
        except ValueError:
            pass
    if not nums:
        return {}
    nums.sort()
    n = len(nums)
    mean = sum(nums) / n
    variance = sum((x - mean) ** 2 for x in nums) / n
    return {
        "min": nums[0],
        "max": nums[-1],
        "mean": round(mean, 4),
        "std": round(math.sqrt(variance), 4),
        "median": nums[n // 2] if n % 2 else (nums[n // 2 - 1] + nums[n // 2]) / 2,
    }


def analyze_csv(content: str, filename: str = "") -> dict[str, Any]:
    """
    Analyse raw CSV text and return statistics useful for claim verification.

    Returns
    -------
    {
        "filename": str,
        "row_count": int,          # data rows (header excluded)
        "column_count": int,
        "columns": [str, ...],
        "column_stats": {
            "<col>": {
                "dtype": "numeric" | "categorical" | "empty",
                "missing_count": int,
                "missing_pct": float,
                "unique_count": int,          # always present
                "sample_values": [str, ...],  # up to 5 non-empty values
                # numeric only:
                "min": float, "max": float, "mean": float, "std": float, "median": float,
            }
        },
        "error": str | None,
    }
    """
    result: dict[str, Any] = {
        "filename": filename,
        "row_count": 0,
        "column_count": 0,
        "columns": [],
        "column_stats": {},
        "error": None,
    }

    try:
        # Detect delimiter
        sample = content[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel  # type: ignore[assignment]

        reader = csv.reader(io.StringIO(content), dialect)
        rows = list(reader)
    except Exception as exc:
        result["error"] = str(exc)
        return result

    if not rows:
        return result

    header = rows[0]
    data_rows = rows[1:]

    # Strip whitespace from header
    columns = [c.strip() for c in header]
    result["columns"] = columns
    result["column_count"] = len(columns)
    result["row_count"] = len(data_rows)

    # Per-column analysis
    for col_idx, col_name in enumerate(columns):
        col_values = []
        for row in data_rows:
            col_values.append(row[col_idx].strip() if col_idx < len(row) else "")

        missing = sum(1 for v in col_values if not v)
        total = len(col_values)
        dtype = _infer_type(col_values)
        non_empty = [v for v in col_values if v]
        unique_count = len(set(col_values)) - (1 if "" in col_values else 0)

        stats: dict[str, Any] = {
            "dtype": dtype,
            "missing_count": missing,
            "missing_pct": round(missing / total * 100, 1) if total else 0.0,
            "unique_count": unique_count,
            "sample_values": list(dict.fromkeys(v for v in non_empty if v))[:5],
        }
        if dtype == "numeric":
            stats.update(_numeric_stats(col_values))

        result["column_stats"][col_name] = stats

    return result


def format_csv_stats_for_prompt(stats: dict[str, Any]) -> str:
    """Render CSV statistics as a compact text block for LLM prompts."""
    lines = [
        f"File: {stats['filename']}",
        f"  Rows (data): {stats['row_count']}",
        f"  Columns ({stats['column_count']}): {', '.join(stats['columns'])}",
    ]

    if stats.get("error"):
        lines.append(f"  ERROR: {stats['error']}")
        return "\n".join(lines)

    lines.append("  Column details:")
    for col, cs in stats.get("column_stats", {}).items():
        missing_info = f"missing={cs['missing_pct']}%" if cs["missing_count"] else "complete"
        unique_info = f"unique={cs['unique_count']}"
        dtype = cs["dtype"]

        if dtype == "numeric":
            num_info = (
                f"min={cs.get('min')}, max={cs.get('max')}, "
                f"mean={cs.get('mean')}, std={cs.get('std')}"
            )
            lines.append(f"    {col}: {dtype}, {missing_info}, {unique_info}, {num_info}")
        else:
            samples = ", ".join(repr(v) for v in cs.get("sample_values", [])[:3])
            lines.append(f"    {col}: {dtype}, {missing_info}, {unique_info}, samples=[{samples}]")

    return "\n".join(lines)