"""
Scoring and report-building logic for VKR repository quality assessment.

Separated from VkrScorer so the scorer class stays focused on orchestration
while this module owns all score-computation, formatting, and persistence.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

# ── Scoring weights ───────────────────────────────────────────────────────────

WEIGHTS_DATA_EXPERIMENT: dict[str, int] = {
    "readme": 20,
    "license": 10,
    "commits": 10,
    "execution_files": 20,
    "requirements": 10,
    "data_files": 10,
    "experiment_scripts": 20,
}

WEIGHTS_APPS: dict[str, int] = {
    "readme": 25,
    "license": 10,
    "commits": 10,
    "execution_files": 25,
    "tests": 30,
}

# ── Display constants ─────────────────────────────────────────────────────────

REPO_TYPE_LABELS: dict[str, str] = {
    "app": "Application",
    "algorithm_experiments": "Algorithm Experiments",
    "model_training_experiments": "Model Training Experiments",
}

CHECK_ORDER: list[str] = [
    "readme",
    "license",
    "commits",
    "requirements",
    "execution_files",
    "repo_type",
    "tests",
    "data_files",
    "experiment_scripts",
    "syntax",
    "docstrings",
]

_APP_TYPES = {"app"}


# ── Engine class ──────────────────────────────────────────────────────────────


class ScoringEngine:
    """Computes VKR quality scores and builds human-readable reports."""

    def __init__(self, repo_url: str) -> None:
        self._repo_url = repo_url

    # ── Score computation ─────────────────────────────────────────────────────

    def compute_score(self, checks: dict, repo_type: str = "unknown") -> tuple[int, dict]:
        """Return *(score_0_100, per_check_breakdown)*."""
        weights = WEIGHTS_APPS if repo_type in _APP_TYPES else WEIGHTS_DATA_EXPERIMENT

        earned = 0
        breakdown: dict = {}

        for name, weight in weights.items():
            result = checks.get(name, {})
            if result.get("applicable") is False:
                breakdown[name] = {"applicable": False}
                continue

            passed = (
                bool(result.get("present") and result.get("meaningful"))
                if name == "readme"
                else bool(result.get("present"))
            )

            pts = weight if passed else 0
            earned += pts
            breakdown[name] = {"weight": weight, "earned": pts, "passed": passed}

        return earned, breakdown

    # ── Report building ───────────────────────────────────────────────────────

    def build_report(self, checks: dict) -> dict:
        """Assemble the full JSON report from raw check results."""
        repo_type = checks.get("repo_type", {}).get("value", "unknown")
        score, breakdown = self.compute_score(checks, repo_type)
        return {
            "repo_url": self._repo_url,
            "analyzed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "checks": checks,
            "summary": {
                "score": score,
                "score_breakdown": breakdown,
                "repo_type": checks.get("repo_type", {}).get("value", "unknown"),
                "syntax": checks.get("syntax", {}),
                "docstrings": checks.get("docstrings", {}),
            },
        }

    def build_text_report(self, report: dict) -> str:
        """Render *report* as a plain-text summary string."""
        checks = report["checks"]
        score = report["summary"]["score"]
        repo_type = report["summary"]["repo_type"]
        type_label = REPO_TYPE_LABELS.get(repo_type, repo_type)

        lines = [
            f"Repository : {report['repo_url']}",
            f"Analyzed   : {report['analyzed_at']}",
            f"Type       : {type_label}",
            "",
            "Checks:",
        ]
        for key in CHECK_ORDER:
            if key in checks:
                lines.append(self.format_check_line(key, checks[key]))

        lines += ["", f"Score: {score}/100"]

        ca = report.get("claims_analysis")
        if ca:
            stats = ca.get("stats", {})
            lines += [
                "",
                "Claims Analysis:",
                f"  Total claims    : {stats.get('total', 0)}",
                f"  Implemented     : {stats.get('implemented', 0)}",
                f"  Implementation  : {stats.get('implementation_rate_pct', 0)}%",
            ]

        return "\n".join(lines)

    def save_results(self, report: dict, output_dir: str) -> tuple[str, str]:
        """Persist *report* as JSON + text files under *output_dir*."""
        target = os.path.join(output_dir, self._sanitize_dir_name(self._repo_url))
        os.makedirs(target, exist_ok=True)

        json_path = os.path.join(target, "report.json")
        txt_path = os.path.join(target, "report.txt")

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(self.build_text_report(report))

        return json_path, txt_path

    # ── Formatting helpers ────────────────────────────────────────────────────

    @staticmethod
    def format_check_line(key: str, val: dict) -> str:
        """Format a single check entry as a fixed-width text line."""
        if key == "repo_type":
            label = REPO_TYPE_LABELS.get(val.get("value", ""), val.get("value", "unknown"))
            conf = val.get("confidence", "")
            return f"  repo_type       : {label} ({conf} confidence)"

        if val.get("applicable") is False:
            return f"  {key:<18}: n/a"

        if key == "readme":
            if not val.get("present"):
                status = "MISSING"
            elif val.get("meaningful") is False:
                status = "present (too short)"
            else:
                chars = val.get("char_count", 0)
                status = f"OK ({chars} chars)"
            return f"  readme          : {status}"

        if key == "commits":
            count = val.get("count", 0)
            status = f"OK (>{5})" if val.get("present") else f"FAIL ({count} commits)"
            return f"  commits         : {status}"

        if key == "syntax":
            return f"  syntax          : {val.get('summary', 'unknown')}"

        if key == "docstrings":
            return f"  docstrings      : {val.get('summary', 'unknown')}"

        status = "OK" if val.get("present") else "MISSING"
        matched = val.get("matched_file") or ", ".join(val.get("verified", [])[:2])
        detail = f" [{matched}]" if matched else ""
        return f"  {key:<18}: {status}{detail}"

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _sanitize_dir_name(repo_url: str) -> str:
        name = repo_url.rstrip("/")
        if "github.com" in name:
            name = name.split("github.com/", 1)[1]
        name = name.replace("/", "__")
        return re.sub(r"[^\w\-.]", "_", name)[:100]
