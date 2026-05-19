"""Weighted 0-100 scoring. Syntax and docstrings are informational only."""

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
