import json
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.tools.repository_analysis.scorecard import ScorecardCheck, ScorecardResult, ScorecardRunner

SAMPLE_JSON = json.dumps({
    "date": "2026-05-28T00:00:00Z",
    "repo": {"name": "file:///tmp/repo", "commit": "unknown"},
    "scorecard": {"version": "v5.5.0", "commit": "abc123"},
    "score": 5.0,
    "checks": [
        {"name": "Binary-Artifacts", "score": 10, "reason": "no binaries found"},
        {"name": "License", "score": 0, "reason": "license file not detected"},
        {"name": "Security-Policy", "score": -1, "reason": "no workflows found"},
    ],
    "metadata": None,
})


def test_run_returns_none_when_binary_missing():
    # Arrange
    runner = ScorecardRunner("/some/repo")

    # Act
    with patch("shutil.which", return_value=None):
        result = runner.run()

    # Assert
    assert result is None


def test_parse_valid_json():
    # Arrange
    runner = ScorecardRunner("/some/repo")

    # Act
    result = runner._parse(SAMPLE_JSON)

    # Assert
    assert result is not None
    assert result.aggregate_score == 5.0
    assert result.date == "2026-05-28T00:00:00Z"
    assert len(result.checks) == 3
    assert result.checks[0].name == "Binary-Artifacts"
    assert result.checks[0].score == 10
    assert result.checks[1].score == 0
    assert result.checks[2].score == -1


def test_parse_skips_na_checks():
    # Arrange
    runner = ScorecardRunner("/some/repo")

    # Act
    result = runner._parse(SAMPLE_JSON)

    # Assert
    na_checks = [c for c in result.checks if c.score == -1]
    visible_checks = [c for c in result.checks if c.score != -1]
    assert len(na_checks) == 1
    assert na_checks[0].name == "Security-Policy"
    assert len(visible_checks) == 2


def test_result_roundtrip():
    # Arrange
    original = ScorecardResult(
        aggregate_score=7.3,
        date="2026-05-28T00:00:00Z",
        checks=[
            ScorecardCheck(name="License", score=10, reason="found"),
            ScorecardCheck(name="Security-Policy", score=-1, reason="N/A"),
        ],
    )

    # Act
    restored = ScorecardResult.from_dict(original.to_dict())

    # Assert
    assert restored.aggregate_score == original.aggregate_score
    assert restored.date == original.date
    assert len(restored.checks) == len(original.checks)
    assert restored.checks[0].name == original.checks[0].name
    assert restored.checks[0].score == original.checks[0].score
    assert restored.checks[1].score == original.checks[1].score


def test_run_returns_none_on_empty_stdout():
    # Arrange
    runner = ScorecardRunner("/some/repo")
    mock_proc = MagicMock()
    mock_proc.stdout = ""
    mock_proc.stderr = "some error"

    # Act
    with patch("shutil.which", return_value="/usr/bin/scorecard"):
        with patch("subprocess.run", return_value=mock_proc):
            result = runner.run()

    # Assert
    assert result is None
