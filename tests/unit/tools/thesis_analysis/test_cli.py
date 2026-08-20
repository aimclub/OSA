"""Tests for the canonical thesis-analysis CLI entry point."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from osa_tool.tools.thesis_analysis import __main__ as thesis_cli


def test_cli_clones_once_and_runs_the_canonical_operation(monkeypatch, tmp_path):
    args = SimpleNamespace(
        repository="https://github.com/example/thesis",
        paper=tmp_path / "paper.pdf",
        claims_json=None,
        output_dir=tmp_path / "output",
        include_low_verifiability=False,
        include_low_confidence=False,
    )
    parser = MagicMock()
    parser.parse_args.return_value = args
    git_agent = MagicMock()
    operation = MagicMock()
    operation.run.return_value = SimpleNamespace(artifacts=SimpleNamespace(json_path=Path("analysis.json")))

    monkeypatch.setattr(thesis_cli, "build_parser", MagicMock(return_value=parser))
    monkeypatch.setattr(thesis_cli, "ConfigManager", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(thesis_cli, "initialize_git_platform", MagicMock(return_value=(git_agent, MagicMock())))
    operation_factory = MagicMock(return_value=operation)
    monkeypatch.setattr(thesis_cli, "ThesisAnalysisOperation", operation_factory)

    assert thesis_cli.main() == 0
    git_agent.clone_repository.assert_called_once_with()
    request = operation_factory.call_args.args[2]
    assert request.repository == args.repository
    assert request.paper_path == args.paper
    assert request.claims_path is None
