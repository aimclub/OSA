import hashlib
import json
import platform
import shutil
import subprocess
import tarfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from osa_tool.utils.logger import logger

_SCORECARD_REPO = "ossf/scorecard"
_SCORECARD_VERSION = "5.5.0"

# Scorecard's --local mode mishandles path separators on Windows, so Dangerous-Workflow,
# Token-Permissions and Pinned-Dependencies come back as -1 whatever the repository holds.
# Until the upstream fix ships, Windows pulls a fork build carrying that two-line patch.
# The download is checksum-verified precisely because it is not an upstream artifact.
# Upstream fix: https://github.com/ossf/scorecard/pull/5089
# Once merged: delete the three constants below and _scorecard_source(), so every platform
# goes back to _SCORECARD_REPO / _SCORECARD_VERSION.
_SCORECARD_WINDOWS_REPO = "Shtirmann/scorecard"
_SCORECARD_WINDOWS_VERSION = "5.5.0-osa.1"
_SCORECARD_WINDOWS_SHA256 = "8e5c9f631955391093bc451ee408e7d905d79c60610bd0e43dea42c4eceb168f"
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
        checks = [
            ScorecardCheck(
                name=c.get("name", ""),
                score=c.get("score") if isinstance(c.get("score"), int) else -1,
                reason=c.get("reason", ""),
            )
            for c in data.get("checks", [])
        ]
        agg = data.get("aggregate_score")
        return cls(
            aggregate_score=float(agg) if isinstance(agg, (int, float)) else 0.0,
            date=data.get("date", ""),
            checks=checks,
        )


def _scorecard_cache_dir() -> Path:
    return Path.home() / ".osa_tool" / "bin"


def _scorecard_source() -> tuple[str, str, str | None]:
    """Return (repo, version, expected_sha256) of the release to install here.

    Windows gets the patched fork build plus a checksum to verify it against; every
    other platform gets the upstream release, where the path-separator bug is absent.
    """
    if platform.system() == "Windows":
        return _SCORECARD_WINDOWS_REPO, _SCORECARD_WINDOWS_VERSION, _SCORECARD_WINDOWS_SHA256
    return _SCORECARD_REPO, _SCORECARD_VERSION, None


def _local_binary_path() -> Path:
    # The resolved version is embedded in the filename, so bumping a version (or
    # switching between the upstream and fork builds) invalidates an older cached
    # binary instead of silently reusing it.
    _, version, _ = _scorecard_source()
    suffix = ".exe" if platform.system() == "Windows" else ""
    return _scorecard_cache_dir() / f"scorecard-{version}{suffix}"


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
    repo, version, expected_sha256 = _scorecard_source()
    if arch is None:
        logger.warning(
            "scorecard auto-install: unsupported architecture '%s'. "
            "Install manually from https://github.com/%s/releases",
            platform.machine(),
            repo,
        )
        return None

    url = f"https://github.com/{repo}/releases/download/v{version}/scorecard_{version}_{system}_{arch}.tar.gz"
    tmp = dest.parent / "scorecard_download.tar.gz"

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        logger.info(
            "Downloading OpenSSF Scorecard v%s from %s for %s/%s...",
            version,
            repo,
            system,
            arch,
        )
        with urllib.request.urlopen(url, timeout=_DOWNLOAD_TIMEOUT) as resp, open(tmp, "wb") as fh:
            shutil.copyfileobj(resp, fh)

        if expected_sha256 is not None:
            actual_sha256 = hashlib.sha256(tmp.read_bytes()).hexdigest()
            if actual_sha256 != expected_sha256:
                raise ValueError(f"checksum mismatch for {url}: expected {expected_sha256}, got {actual_sha256}")

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
            "  Install manually from https://github.com/%s/releases/tag/v%s\n"
            "  and add to PATH. Scorecard section will be skipped.",
            e,
            repo,
            version,
        )
        return None
    finally:
        tmp.unlink(missing_ok=True)


def _resolve_scorecard_binary() -> str | None:
    """Return path to scorecard binary: PATH → local cache → auto-download.

    The PATH lookup is skipped on Windows: a scorecard found there is almost certainly a
    stock build, which silently scores most checks -1 in --local mode. Falling through to
    our checksum-verified fork build keeps the report honest instead of fast.
    """
    if platform.system() != "Windows":
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
        # Scorecard analysis must never abort the OSA run; swallow any failure
        # (binary resolution, download, subprocess, parsing) and skip gracefully.
        try:
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
        except Exception as e:
            logger.warning("Scorecard analysis failed unexpectedly: %s; skipping.", e)
            return None

    def _parse(self, json_str: str) -> ScorecardResult | None:
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse scorecard JSON output: %s", e)
            return None

        checks = [
            ScorecardCheck(
                name=c["name"],
                score=c.get("score") if isinstance(c.get("score"), int) else -1,
                reason=c.get("reason", ""),
            )
            for c in data.get("checks", [])
        ]
        agg = data.get("score")
        return ScorecardResult(
            aggregate_score=float(agg) if isinstance(agg, (int, float)) else 0.0,
            date=data.get("date", ""),
            checks=checks,
        )
