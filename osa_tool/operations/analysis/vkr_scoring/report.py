"""Build VKR scoring report (JSON + human-readable text)."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from .scoring import compute_score

_REPO_TYPE_LABELS = {
    "app": "Application",
    "algorithm_experiments": "Algorithm Experiments",
    "model_training_experiments": "Model Training Experiments",
}

_CHECK_ORDER = [
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


def build_report(checks: dict, repo_url: str) -> dict:
    repo_type = checks.get("repo_type", {}).get("value", "unknown")
    score, breakdown = compute_score(checks, repo_type)
    return {
        "repo_url": repo_url,
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


def _format_check_line(key: str, val: dict) -> str:
    if key == "repo_type":
        label = _REPO_TYPE_LABELS.get(val.get("value", ""), val.get("value", "unknown"))
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


def build_text_report(report: dict) -> str:
    checks = report["checks"]
    score = report["summary"]["score"]
    repo_type = report["summary"]["repo_type"]
    type_label = _REPO_TYPE_LABELS.get(repo_type, repo_type)

    lines = [
        f"Repository : {report['repo_url']}",
        f"Analyzed   : {report['analyzed_at']}",
        f"Type       : {type_label}",
        "",
        "Checks:",
    ]
    for key in _CHECK_ORDER:
        if key in checks:
            lines.append(_format_check_line(key, checks[key]))

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


def _sanitize_dir_name(repo_url: str) -> str:
    name = repo_url.rstrip("/")
    if "github.com" in name:
        name = name.split("github.com/", 1)[1]
    name = name.replace("/", "__")
    return re.sub(r"[^\w\-.]", "_", name)[:100]


def save_results(report: dict, output_dir: str) -> tuple[str, str]:
    target = os.path.join(output_dir, _sanitize_dir_name(report["repo_url"]))
    os.makedirs(target, exist_ok=True)

    json_path = os.path.join(target, "report.json")
    txt_path = os.path.join(target, "report.txt")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(build_text_report(report))

    return json_path, txt_path
