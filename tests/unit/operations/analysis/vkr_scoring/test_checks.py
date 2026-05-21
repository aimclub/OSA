"""Tests for VKR checks — pure/static logic, no LLM or real file I/O required."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

import pytest

from osa_tool.operations.analysis.vkr_scoring.checks import (
    VkrChecker,
    VkrConfig,
    _sample_tree,
    build_file_tree,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_config(clone_dir: str = "/tmp") -> VkrConfig:
    return VkrConfig(
        clone_dir=clone_dir,
        repo_url="https://github.com/test/repo",
        repo=MagicMock(),
        model_handler=MagicMock(),
    )


# ── _sample_tree ──────────────────────────────────────────────────────────────


def test_sample_tree_limits_per_dir():
    paths = [f"src/file{i}.py" for i in range(20)]
    result = _sample_tree(paths, max_per_dir=3, max_total=500)
    assert len(result) == 3


def test_sample_tree_total_limit():
    paths = [f"dir{i // 10}/file{i}.py" for i in range(600)]
    result = _sample_tree(paths, max_per_dir=100, max_total=500)
    assert len(result) <= 500


# ── check_readme ──────────────────────────────────────────────────────────────


def test_check_readme_missing():
    checker = VkrChecker(_make_config())
    result = checker.check_readme([])
    assert result["present"] is False


def test_check_readme_present(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("x" * 300, encoding="utf-8")
    checker = VkrChecker(_make_config(clone_dir=str(tmp_path)))
    result = checker.check_readme(["README.md"])
    assert result["present"] is True
    assert result["meaningful"] is True


def test_check_readme_present_too_short(tmp_path):
    readme = tmp_path / "README.md"
    readme.write_text("short", encoding="utf-8")
    checker = VkrChecker(_make_config(clone_dir=str(tmp_path)))
    result = checker.check_readme(["README.md"])
    assert result["present"] is True
    assert result["meaningful"] is False


# ── check_license ─────────────────────────────────────────────────────────────


def test_check_license_present():
    checker = VkrChecker(_make_config())
    result = checker.check_license(["src/main.py", "LICENSE", "README.md"])
    assert result["present"] is True
    assert result["matched_file"] == "LICENSE"


def test_check_license_missing():
    checker = VkrChecker(_make_config())
    result = checker.check_license(["src/main.py", "README.md"])
    assert result["present"] is False


# ── check_requirements ────────────────────────────────────────────────────────


def test_check_requirements_present():
    checker = VkrChecker(_make_config())
    result = checker.check_requirements(["src/main.py", "requirements.txt"])
    assert result["present"] is True


def test_check_requirements_missing():
    checker = VkrChecker(_make_config())
    result = checker.check_requirements(["src/main.py"])
    assert result["present"] is False


# ── build_file_tree ───────────────────────────────────────────────────────────


def test_build_file_tree(tmp_path):
    (tmp_path / "main.py").write_text("# main", encoding="utf-8")
    subdir = tmp_path / "src"
    subdir.mkdir()
    (subdir / "utils.py").write_text("# utils", encoding="utf-8")

    flat_paths, all_paths = build_file_tree(str(tmp_path))

    assert "main.py" in flat_paths
    assert "src/utils.py" in flat_paths
    assert "src" in all_paths


# ── check_commits ─────────────────────────────────────────────────────────────


def test_check_commits_above_threshold():
    mock_repo = MagicMock()
    mock_repo.iter_commits.return_value = iter([MagicMock()] * 6)
    config = VkrConfig(
        clone_dir="/tmp",
        repo_url="https://github.com/test/repo",
        repo=mock_repo,
        model_handler=MagicMock(),
    )
    checker = VkrChecker(config)
    result = checker.check_commits()
    assert result["present"] is True


def test_check_commits_below_threshold():
    mock_repo = MagicMock()
    mock_repo.iter_commits.return_value = iter([MagicMock()] * 3)
    config = VkrConfig(
        clone_dir="/tmp",
        repo_url="https://github.com/test/repo",
        repo=mock_repo,
        model_handler=MagicMock(),
    )
    checker = VkrChecker(config)
    result = checker.check_commits()
    assert result["present"] is False


# ── check_syntax ─────────────────────────────────────────────────────────────


def test_check_syntax_no_python(tmp_path):
    checker = VkrChecker(_make_config(clone_dir=str(tmp_path)))
    result = checker.check_syntax([])
    assert result["ok"] is True
    assert "no Python files" in result["summary"]


# ── check_docstrings ──────────────────────────────────────────────────────────


def test_check_docstrings_no_python(tmp_path):
    checker = VkrChecker(_make_config(clone_dir=str(tmp_path)))
    result = checker.check_docstrings([])
    assert result["coverage_pct"] is None


def test_check_docstrings_with_functions(tmp_path):
    py_file = tmp_path / "module.py"
    py_file.write_text(
        'def documented():\n    """This has a docstring."""\n    pass\n\ndef undocumented():\n    pass\n',
        encoding="utf-8",
    )
    checker = VkrChecker(_make_config(clone_dir=str(tmp_path)))
    result = checker.check_docstrings(["module.py"])
    assert result["total"] == 2
    assert result["documented"] == 1
    assert result["coverage_pct"] == 50
