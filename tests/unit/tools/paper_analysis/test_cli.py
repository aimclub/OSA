"""Tests for the focused and main paper-analysis commands."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from osa_tool.config.settings import PaperAnalysisSettings
from osa_tool.tools.paper_analysis import cli


def _args(tmp_path, **overrides):
    values = {
        "repository": "https://github.com/example/project",
        "paper": tmp_path / "paper.pdf",
        "claims_json": None,
        "paper_output_dir": None,
        "include_repository_quality": None,
        "only_high_medium_verifiability": None,
        "hide_low_confidence": None,
        "delete_dir": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_request_uses_config_and_cli_quality_policy(tmp_path):
    config_manager = MagicMock()
    config_manager.get_paper_analysis_settings.return_value = PaperAnalysisSettings(
        output_dir=Path("paper-results"),
        include_repository_quality=True,
    )

    configured = cli.build_request(_args(tmp_path), config_manager, clone_dir=tmp_path / "repository")
    overridden = cli.build_request(
        _args(tmp_path, include_repository_quality=False),
        config_manager,
        clone_dir=tmp_path / "repository",
    )

    assert configured.include_repository_quality is True
    assert overridden.include_repository_quality is False
    assert configured.output_dir == tmp_path / "paper-results" / "repository"


def test_shared_runner_clones_once_and_cleans_a_created_remote_clone(monkeypatch, tmp_path):
    args = _args(tmp_path, delete_dir=True)
    config_manager = MagicMock()
    config_manager.get_paper_analysis_settings.return_value = PaperAnalysisSettings(output_dir=tmp_path / "output")
    git_agent = MagicMock(clone_dir=str(tmp_path / "clone"))
    operation = MagicMock()
    operation.run.return_value = "result"
    cleanup = MagicMock()

    class FakeProgress:
        def __init__(self, _description):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def update(self, *_args):
            return None

    monkeypatch.setattr(cli, "RichStageProgress", FakeProgress)
    monkeypatch.setattr(cli, "delete_created_remote_clone", cleanup)

    assert (
        cli.run_paper_analysis(
            args,
            config_manager_factory=lambda _args: config_manager,
            git_initializer=lambda _args, _config: (git_agent, MagicMock()),
            operation_factory=lambda _config, _git, _request: operation,
        )
        == "result"
    )

    git_agent.clone_repository.assert_called_once_with()
    cleanup.assert_called_once_with(args.repository, git_agent.clone_dir, existed_before_clone=False)
