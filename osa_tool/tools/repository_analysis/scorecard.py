import json
import shutil
import subprocess
from dataclasses import dataclass

from osa_tool.utils.logger import logger

SCORECARD_CHECKS = [
    "Binary-Artifacts",
    "Dangerous-Workflow",
    "License",
    "Pinned-Dependencies",
    "Security-Policy",
    "Token-Permissions",
]
_CHECKS_ARG = ",".join(SCORECARD_CHECKS)


@dataclass
class ScorecardCheck:
    name: str
    score: int  # 0–10; -1 = not applicable (API-dependent or no relevant files)
    reason: str


@dataclass
class ScorecardResult:
    aggregate_score: float
    date: str
    checks: list[ScorecardCheck]

    def to_dict(self) -> dict:
        return {
            "aggregate_score": self.aggregate_score,
            "date": self.date,
            "checks": [{"name": c.name, "score": c.score, "reason": c.reason} for c in self.checks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ScorecardResult":
        checks = [
            ScorecardCheck(name=c["name"], score=c["score"], reason=c["reason"])
            for c in data.get("checks", [])
        ]
        return cls(aggregate_score=data["aggregate_score"], date=data["date"], checks=checks)


class ScorecardRunner:
    """Runs the scorecard CLI binary in --local mode on a repository directory.

    Only file-based checks are used (no GitHub API calls) to keep execution fast
    and allow before/after comparison within a single OSA run.
    """

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path

    def run(self) -> ScorecardResult | None:
        binary = shutil.which("scorecard")
        if binary is None:
            logger.warning(
                "scorecard binary not found on PATH; skipping Scorecard analysis. "
                "Install from https://github.com/ossf/scorecard/releases"
            )
            return None

        try:
            proc = subprocess.run(
                [binary, "--local", self.repo_path, "--checks", _CHECKS_ARG, "--format", "json"],
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            logger.warning("scorecard timed out after 120 s; skipping Scorecard analysis")
            return None
        except OSError as e:
            logger.warning("Failed to run scorecard binary: %s", e)
            return None

        if not proc.stdout.strip():
            logger.warning("scorecard produced no output (stderr: %s)", proc.stderr[:200])
            return None

        return self._parse(proc.stdout)

    def _parse(self, json_str: str) -> ScorecardResult | None:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse scorecard JSON output: %s", e)
            return None

        checks = [
            ScorecardCheck(
                name=c["name"],
                score=c.get("score", -1),
                reason=c.get("reason", ""),
            )
            for c in data.get("checks", [])
        ]
        return ScorecardResult(
            aggregate_score=float(data.get("score", 0.0)),
            date=data.get("date", ""),
            checks=checks,
        )
