import json
import platform
import shutil
import subprocess
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from osa_tool.utils.logger import logger

_SCORECARD_VERSION = "5.5.0"
_DOWNLOAD_TIMEOUT = 30  # seconds
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
        checks = [ScorecardCheck(name=c["name"], score=c["score"], reason=c["reason"]) for c in data.get("checks", [])]
        return cls(aggregate_score=data["aggregate_score"], date=data["date"], checks=checks)


def _scorecard_cache_dir() -> Path:
    return Path.home() / ".osa_tool" / "bin"


def _local_binary_path() -> Path:
    # Version is embedded in the filename so that bumping _SCORECARD_VERSION
    # invalidates an older cached binary instead of silently reusing it.
    suffix = ".exe" if platform.system() == "Windows" else ""
    return _scorecard_cache_dir() / f"scorecard-{_SCORECARD_VERSION}{suffix}"


def _download_scorecard(dest: Path) -> str | None:
    """Download the scorecard binary from GitHub Releases and cache it at dest."""
    system = platform.system().lower()
    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }
    arch = arch_map.get(platform.machine().lower())
    if arch is None:
        logger.warning(
            "scorecard auto-install: unsupported architecture '%s'. "
            "Install manually from https://github.com/ossf/scorecard/releases",
            platform.machine(),
        )
        return None

    url = (
        f"https://github.com/ossf/scorecard/releases/download/"
        f"v{_SCORECARD_VERSION}/scorecard_{_SCORECARD_VERSION}_{system}_{arch}.tar.gz"
    )
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / "scorecard_download.tar.gz"

    try:
        logger.info(
            "Downloading OpenSSF Scorecard v%s for %s/%s...",
            _SCORECARD_VERSION,
            system,
            arch,
        )
        with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as resp, open(tmp, "wb") as fh:
            shutil.copyfileobj(resp, fh)
        exe_name = "scorecard.exe" if system == "windows" else "scorecard"
        with tarfile.open(tmp) as tf:
            member = tf.extractfile(exe_name)
            if member is None:
                raise ValueError(f"{exe_name} not found in archive")
            dest.write_bytes(member.read())
        if system != "windows":
            dest.chmod(0o755)
        logger.info("Scorecard installed to %s", dest)
        return str(dest)
    except Exception as e:
        logger.warning(
            "Failed to auto-install scorecard: %s\n"
            "  Install manually from https://github.com/ossf/scorecard/releases/tag/v%s\n"
            "  and add to PATH. Scorecard section will be skipped.",
            e,
            _SCORECARD_VERSION,
        )
        return None
    finally:
        tmp.unlink(missing_ok=True)


def _resolve_scorecard_binary() -> str | None:
    """Return path to scorecard binary: PATH → local cache → auto-download."""
    if platform.system() == "Windows":
        # Scorecard's --local mode is unreliable on Windows: most checks return
        # N/A regardless of repo state (path-separator handling in scorecard),
        # which would produce misleading report sections. Skip gracefully until
        # the upstream fix lands. See https://github.com/ossf/scorecard/pull/5089
        logger.warning(
            "OpenSSF Scorecard --local mode is unreliable on Windows; "
            "skipping Scorecard analysis. Run on Linux/macOS for full results."
        )
        return None
    binary = shutil.which("scorecard")
    if binary:
        return binary
    local = _local_binary_path()
    if local.exists():
        return str(local)
    return _download_scorecard(local)


class ScorecardRunner:
    """Runs the scorecard CLI binary in --local mode on a repository directory.

    Only file-based checks are used (no GitHub API calls) to keep execution fast
    and allow before/after comparison within a single OSA run.
    """

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path

    def run(self) -> ScorecardResult | None:
        binary = _resolve_scorecard_binary()
        if binary is None:
            return None

        try:
            proc = subprocess.run(
                [
                    binary,
                    "--local",
                    ".",
                    "--checks",
                    _CHECKS_ARG,
                    "--format",
                    "json",
                ],
                cwd=self.repo_path,
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
