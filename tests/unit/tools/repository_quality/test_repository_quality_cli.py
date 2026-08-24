"""Tests for the focused repository-quality command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from osa_tool.tools.repository_quality import __main__ as quality_cli


def test_quality_tool_clones_once_and_writes_the_existing_report(monkeypatch, tmp_path, capsys):
    args = SimpleNamespace(repository="https://github.com/example/repository", output_dir=tmp_path / "output")
    parser = MagicMock()
    parser.parse_args.return_value = args
    git_agent = MagicMock()
    scorer = MagicMock()
    scorer.run.return_value = {"result": {"json_path": "quality.json"}}

    class FakeProgress:
        def __init__(self, _description):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def update(self, *_args):
            return None

    monkeypatch.setattr(quality_cli, "build_parser", MagicMock(return_value=parser))
    monkeypatch.setattr(quality_cli, "configure_focused_tool_logging", MagicMock())
    monkeypatch.setattr(quality_cli, "ConfigManager", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(quality_cli, "initialize_git_platform", MagicMock(return_value=(git_agent, MagicMock())))
    monkeypatch.setattr(quality_cli, "RepositoryQualityScorer", MagicMock(return_value=scorer))
    monkeypatch.setattr(quality_cli, "RichStageProgress", FakeProgress)

    assert quality_cli.main() == 0
    git_agent.clone_repository.assert_called_once_with()
    scorer.run.assert_called_once_with()
    assert capsys.readouterr().out == "quality.json\n"
