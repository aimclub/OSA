"""Tests for claim pipeline logic — no LLM needed."""

from __future__ import annotations

import pytest

from osa_tool.utils.response_cleaner import JsonParseError
from osa_tool.operations.analysis.vkr_scoring.claims import ClaimsPipeline

# ── _parse_json_list ──────────────────────────────────────────────────────────


def test_parse_json_list_valid():
    result = ClaimsPipeline._parse_json_list('[{"a": 1}]')
    assert isinstance(result, list)
    assert result[0]["a"] == 1


def test_parse_json_list_invalid_json():
    with pytest.raises(JsonParseError):
        ClaimsPipeline._parse_json_list("not valid json {{{")


def test_parse_json_list_not_a_list():
    with pytest.raises(JsonParseError):
        ClaimsPipeline._parse_json_list('{"key": "val"}')


# ── _candidate_files ──────────────────────────────────────────────────────────


def test_candidate_files_matches_patterns():
    filenames = [
        "train.py",
        "model.py",
        "data.py",
        "README.md",
        "setup.py",
    ]
    result = ClaimsPipeline._candidate_files(filenames)
    assert "train.py" in result
    assert "model.py" in result
    assert "data.py" in result
    # setup.py should not match any candidate pattern
    assert "README.md" not in result


# ── _truncate ─────────────────────────────────────────────────────────────────


def test_truncate_long_text():
    lines = [f"line {i}" for i in range(300)]
    text = "\n".join(lines)
    result = ClaimsPipeline._truncate(text, max_lines=250)
    result_lines = result.splitlines()
    assert len(result_lines) <= 251  # 250 lines + truncation note
    assert "truncated" in result


def test_truncate_short_text():
    lines = [f"line {i}" for i in range(10)]
    text = "\n".join(lines)
    result = ClaimsPipeline._truncate(text, max_lines=250)
    assert result == text
