"""Tests for ScoringEngine.compute_score — scoring logic in scoring_engine.py."""

from __future__ import annotations

import pytest

from osa_tool.operations.analysis.vkr_scoring.scoring_engine import (
    WEIGHTS_APPS,
    WEIGHTS_DATA_EXPERIMENT,
    ScoringEngine,
)

_engine = ScoringEngine("https://github.com/test/repo")
compute_score = _engine.compute_score


def _all_pass(weights: dict) -> dict:
    """Build a checks dict where every key in weights has present=True (and for readme, meaningful=True)."""
    checks = {}
    for name in weights:
        if name == "readme":
            checks[name] = {"present": True, "meaningful": True}
        else:
            checks[name] = {"present": True}
    return checks


def _all_fail(weights: dict) -> dict:
    """Build a checks dict where every key in weights has present=False."""
    checks = {}
    for name in weights:
        if name == "readme":
            checks[name] = {"present": False, "meaningful": False}
        else:
            checks[name] = {"present": False}
    return checks


def test_score_full_experiment_repo():
    checks = _all_pass(WEIGHTS_DATA_EXPERIMENT)
    score, breakdown = compute_score(checks, repo_type="model_training_experiments")
    assert score == 100


def test_score_zero_experiment_repo():
    checks = _all_fail(WEIGHTS_DATA_EXPERIMENT)
    score, breakdown = compute_score(checks, repo_type="model_training_experiments")
    assert score == 0


def test_score_app_uses_app_weights():
    # App type: tests count, requirements don't matter
    checks = _all_pass(WEIGHTS_APPS)
    score, breakdown = compute_score(checks, repo_type="app")
    assert score == 100
    # Verify tests key is in breakdown, requirements is not
    assert "tests" in breakdown
    assert "requirements" not in breakdown


def test_score_not_applicable_skipped():
    """A check with applicable=False should not reduce earned points."""
    # Use experiment weights but mark data_files as not applicable
    checks = _all_pass(WEIGHTS_DATA_EXPERIMENT)
    checks["data_files"] = {"applicable": False}
    score, breakdown = compute_score(checks, repo_type="model_training_experiments")
    # data_files (weight 10) is excluded from denominator.
    # Remaining weights sum: 20+10+10+20+10+20 = 90 → all pass → earned == 90
    expected_without_data = sum(v for k, v in WEIGHTS_DATA_EXPERIMENT.items() if k != "data_files")
    assert score == expected_without_data
    assert breakdown["data_files"] == {"applicable": False}
    # Verify the applicable check doesn't count against earned
    for key, val in breakdown.items():
        if key == "data_files":
            continue
        assert val.get("passed") is True
