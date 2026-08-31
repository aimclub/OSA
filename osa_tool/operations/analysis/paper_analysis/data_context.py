"""Lightweight tabular-data context for thesis claim verification."""

from __future__ import annotations

import csv
import io
import math
from typing import Any


class CsvAnalyzer:
    """Summarize raw CSV or TSV text for repository-claim verification."""

    def __init__(self, content: str, filename: str = "") -> None:
        self._content = content
        self._filename = filename

    def analyze(self) -> dict[str, Any]:
        """Return schema, missing-value, sample, and numeric statistics."""
        result: dict[str, Any] = {
            "filename": self._filename,
            "row_count": 0,
            "column_count": 0,
            "columns": [],
            "column_stats": {},
            "error": None,
        }
        try:
            sample = self._content[:4096]
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel  # type: ignore[assignment]
            rows = list(csv.reader(io.StringIO(self._content), dialect))
        except Exception as exc:
            result["error"] = str(exc)
            return result

        if not rows:
            return result

        columns = [column.strip() for column in rows[0]]
        data_rows = rows[1:]
        result["columns"] = columns
        result["column_count"] = len(columns)
        result["row_count"] = len(data_rows)
        for column_index, column_name in enumerate(columns):
            values = [row[column_index].strip() if column_index < len(row) else "" for row in data_rows]
            missing_count = sum(1 for value in values if not value)
            non_empty = [value for value in values if value]
            dtype = self._infer_type(values)
            stats: dict[str, Any] = {
                "dtype": dtype,
                "missing_count": missing_count,
                "missing_pct": round(missing_count / len(values) * 100, 1) if values else 0.0,
                "unique_count": len(set(non_empty)),
                "sample_values": list(dict.fromkeys(non_empty))[:5],
            }
            if dtype == "numeric":
                stats.update(self._numeric_stats(values))
            result["column_stats"][column_name] = stats
        return result

    @staticmethod
    def _infer_type(values: list[str]) -> str:
        non_empty = [value for value in values if value.strip()]
        if not non_empty:
            return "empty"
        numeric_count = 0
        for value in non_empty:
            try:
                float(value.replace(",", "."))
                numeric_count += 1
            except ValueError:
                pass
        return "numeric" if numeric_count / len(non_empty) >= 0.8 else "categorical"

    @staticmethod
    def _numeric_stats(values: list[str]) -> dict[str, Any]:
        numbers: list[float] = []
        for value in values:
            try:
                if value.strip():
                    numbers.append(float(value.replace(",", ".")))
            except ValueError:
                pass
        if not numbers:
            return {}
        numbers.sort()
        count = len(numbers)
        mean = sum(numbers) / count
        variance = sum((number - mean) ** 2 for number in numbers) / count
        return {
            "min": numbers[0],
            "max": numbers[-1],
            "mean": round(mean, 4),
            "std": round(math.sqrt(variance), 4),
            "median": numbers[count // 2] if count % 2 else (numbers[count // 2 - 1] + numbers[count // 2]) / 2,
        }

    @staticmethod
    def format_for_prompt(stats: dict[str, Any]) -> str:
        """Render statistics as a compact LLM prompt block."""
        lines = [
            f"File: {stats['filename']}",
            f"  Rows (data): {stats['row_count']}",
            f"  Columns ({stats['column_count']}): {', '.join(stats['columns'])}",
        ]
        if stats.get("error"):
            lines.append(f"  ERROR: {stats['error']}")
            return "\n".join(lines)

        lines.append("  Column details:")
        for column, column_stats in stats.get("column_stats", {}).items():
            missing = f"missing={column_stats['missing_pct']}%" if column_stats["missing_count"] else "complete"
            unique = f"unique={column_stats['unique_count']}"
            if column_stats["dtype"] == "numeric":
                numeric = (
                    f"min={column_stats.get('min')}, max={column_stats.get('max')}, "
                    f"mean={column_stats.get('mean')}, std={column_stats.get('std')}"
                )
                lines.append(f"    {column}: numeric, {missing}, {unique}, {numeric}")
            else:
                samples = ", ".join(repr(value) for value in column_stats.get("sample_values", [])[:3])
                lines.append(f"    {column}: {column_stats['dtype']}, {missing}, {unique}, samples=[{samples}]")
        return "\n".join(lines)
