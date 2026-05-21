"""
VkrScorer — OSA operation that runs VKR-style repository quality scoring.

Reuses OSA's already-cloned repository (via GitAgent), its ModelHandler for LLM
calls, and pdfplumber (already in OSA requirements) for PDF parsing.

Steps:
  1. Build file tree from the local clone (no extra GitHub API calls).
  2. Run quality checks: README, license, commits, LLM-based entry-points / repo
     type / tests / data files / experiment scripts, syntax, docstrings.
  3. If a paper path is provided: parse PDF → extract claims → verify against code.
  4. Save JSON + text reports to output_dir.
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.utils.logger import logger

from .checks import VkrConfig, build_file_tree, run_all_checks
from .claims import extract_claims, verify_claims

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

_APP_TYPES = {"app"}


def compute_score(checks: dict, repo_type: str = "unknown") -> tuple[int, dict]:
    """Return (score_0_100, per_check_breakdown)."""
    weights = WEIGHTS_APPS if repo_type in _APP_TYPES else WEIGHTS_DATA_EXPERIMENT

    earned = 0
    max_points = 0
    breakdown: dict = {}

    for name, weight in weights.items():
        result = checks.get(name, {})
        if result.get("applicable") is False:
            breakdown[name] = {"applicable": False}
            continue

        if name == "readme":
            passed = bool(result.get("present") and result.get("meaningful"))
        else:
            passed = bool(result.get("present"))

        pts = weight if passed else 0
        earned += pts
        max_points += weight
        breakdown[name] = {"weight": weight, "earned": pts, "passed": passed}

    return earned, breakdown


# ── Report building ───────────────────────────────────────────────────────────

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


# ── Main scorer class ─────────────────────────────────────────────────────────


class VkrScorer:
    """Runs VKR repository quality scoring as an OSA operation."""

    def __init__(
        self,
        config_manager: ConfigManager,
        git_agent: GitAgent,
        paper_path: Optional[str] = None,
        output_dir: Optional[str] = None,
    ):
        self._config_manager = config_manager
        self._git_agent = git_agent
        self._paper_path = paper_path
        self._output_dir = output_dir or os.getcwd()

        model_settings = config_manager.get_model_settings("validation")
        model_handler = ModelHandlerFactory.build(model_settings)

        self._vkr_config = VkrConfig(
            clone_dir=git_agent.clone_dir,
            repo_url=str(config_manager.config.git.repository),
            repo=git_agent.repo,
            model_handler=model_handler,
        )

    def get_quality_report(self) -> dict:
        """Run quality checks only and return the report dict.

        Does not save files, does not process a paper or claims.
        Intended for embedding the VKR score section into another report
        (e.g. the Paper Validation PDF).
        """
        config = self._vkr_config
        logger.info(f"VKR quality checks: {config.repo_url}")
        flat_paths, all_paths = build_file_tree(config.clone_dir)
        checks = run_all_checks(flat_paths, all_paths, config)
        return build_report(checks, config.repo_url)

    def run(self) -> dict:
        config = self._vkr_config
        logger.info(f"VKR scoring: {config.repo_url}")

        logger.info("Building file tree from local clone...")
        flat_paths, all_paths = build_file_tree(config.clone_dir)

        logger.info("Running quality checks...")
        checks = run_all_checks(flat_paths, all_paths, config)
        report = build_report(checks, config.repo_url)

        paper_sections = self._load_paper_sections()
        if paper_sections:
            logger.info("Extracting claims from paper...")
            claims = extract_claims(paper_sections, config)
            if claims:
                logger.info(f"Verifying {len(claims)} claims against repository...")
                report["claims_analysis"] = verify_claims(claims, flat_paths, config)
            else:
                logger.warning("No claims extracted from paper.")
                report["claims_analysis"] = {
                    "claims": [],
                    "stats": {
                        "total": 0,
                        "implemented": 0,
                        "implementation_rate": 0.0,
                        "implementation_rate_pct": 0,
                    },
                }

        json_path, txt_path = save_results(report, self._output_dir)
        logger.info(f"VKR report saved: {json_path}")
        logger.info(f"               : {txt_path}")

        print("\n" + build_text_report(report), file=sys.stderr)

        return {
            "result": {
                "json_path": json_path,
                "txt_path": txt_path,
                "score": report["summary"]["score"],
            }
        }

    def _load_paper_sections(self) -> Optional[list[dict]]:
        if not self._paper_path:
            return None

        path = Path(self._paper_path)
        if not path.exists():
            logger.warning(f"Paper path does not exist: {self._paper_path}")
            return None

        logger.info(f"Parsing paper: {self._paper_path}")
        from .pdf_parser import parse_pdf_to_sections

        sections = parse_pdf_to_sections(path.read_bytes())
        logger.info(f"Parsed {len(sections)} sections from paper.")

        sections_out = Path(self._output_dir) / "paper_sections.json"
        sections_out.parent.mkdir(parents=True, exist_ok=True)
        sections_out.write_text(json.dumps(sections, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"Paper sections saved: {sections_out}")
        return sections
