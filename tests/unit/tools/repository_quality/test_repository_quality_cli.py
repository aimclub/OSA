"""Tests for the focused repository-quality command."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from osa_tool.tools.repository_quality import __main__ as quality_cli


def test_quality_tool_clones_once_and_writes_the_existing_report(monkeypatch, tmp_path, capsys):
    args = SimpleNamespace(
        repository="https://github.com/example/repository",
        output_dir=tmp_path / "output",
        delete_dir=False,
    )
    parser = MagicMock()
    parser.parse_args.return_value = args
    git_agent = MagicMock(clone_dir=str(tmp_path / "repository"))
    scorer = MagicMock()
    scorer.run.return_value = {"result": {"json_path": "quality.json"}}
    config_manager = MagicMock()
    config_manager.config.git.repository = args.repository

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
    monkeypatch.setattr(quality_cli, "ConfigManager", MagicMock(return_value=config_manager))
    monkeypatch.setattr(quality_cli, "initialize_git_platform", MagicMock(return_value=(git_agent, MagicMock())))
    monkeypatch.setattr(quality_cli, "RepositoryQualityScorer", MagicMock(return_value=scorer))
    monkeypatch.setattr(quality_cli, "RichStageProgress", FakeProgress)

    assert quality_cli.main() == 0
    git_agent.clone_repository.assert_called_once_with()
    scorer.run.assert_called_once_with()
    assert capsys.readouterr().out == "quality.json\n"


def test_quality_tool_resolves_omitted_output_outside_the_clone(tmp_path):
    clone_dir = tmp_path / "repository"
    clone_dir.mkdir()

    output_dir = quality_cli.resolve_output_dir(
        None,
        clone_dir=clone_dir,
        repository="https://github.com/example/repository",
    )

    assert output_dir == tmp_path / "repository_quality"
    assert not output_dir.exists()


def test_quality_tool_relocates_a_colliding_default_output(tmp_path):
    clone_dir = tmp_path / "repository_quality"
    clone_dir.mkdir()

    output_dir = quality_cli.resolve_output_dir(
        None,
        clone_dir=clone_dir,
        repository="https://github.com/example/repository_quality",
    )

    assert output_dir == tmp_path / "repository_quality.osa-artifacts"
    assert not output_dir.exists()


@pytest.mark.parametrize(
    "output_dir",
    [
        lambda clone_dir: clone_dir / "quality",
        lambda clone_dir: clone_dir.parent,
    ],
)
def test_quality_tool_rejects_explicit_output_that_would_write_inside_clone(tmp_path, output_dir):
    clone_dir = tmp_path / "repository"
    clone_dir.mkdir()

    with pytest.raises(ValueError, match="cannot be the analyzed repository"):
        quality_cli.resolve_output_dir(
            output_dir(clone_dir),
            clone_dir=clone_dir,
            repository="repository",
        )


def test_quality_tool_rejects_in_clone_output_before_scoring(monkeypatch, tmp_path):
    clone_dir = tmp_path / "repository"
    clone_dir.mkdir()
    args = SimpleNamespace(repository=str(clone_dir), output_dir=clone_dir / "quality", delete_dir=False)
    parser = MagicMock()
    parser.parse_args.return_value = args
    git_agent = MagicMock(clone_dir=str(clone_dir))
    config_manager = MagicMock()
    config_manager.config.git.repository = args.repository
    scorer_factory = MagicMock()

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
    monkeypatch.setattr(quality_cli, "ConfigManager", MagicMock(return_value=config_manager))
    monkeypatch.setattr(quality_cli, "initialize_git_platform", MagicMock(return_value=(git_agent, MagicMock())))
    monkeypatch.setattr(quality_cli, "RepositoryQualityScorer", scorer_factory)
    monkeypatch.setattr(quality_cli, "RichStageProgress", FakeProgress)

    assert quality_cli.main() == 1
    scorer_factory.assert_not_called()
    assert not (clone_dir / "quality").exists()


@pytest.mark.parametrize("fails", [False, True])
def test_quality_tool_cleans_up_a_new_remote_clone_on_success_and_failure(monkeypatch, tmp_path, fails):
    args = SimpleNamespace(
        repository="https://github.com/example/repository",
        output_dir=tmp_path / "output",
        delete_dir=True,
    )
    parser = MagicMock()
    parser.parse_args.return_value = args
    git_agent = MagicMock(clone_dir=str(tmp_path / "repository"))
    config_manager = MagicMock()
    config_manager.config.git.repository = args.repository
    scorer = MagicMock()
    if fails:
        scorer.run.side_effect = RuntimeError("scoring failed")
    else:
        scorer.run.return_value = {"result": {"json_path": "quality.json"}}
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

    monkeypatch.setattr(quality_cli, "build_parser", MagicMock(return_value=parser))
    monkeypatch.setattr(quality_cli, "configure_focused_tool_logging", MagicMock())
    monkeypatch.setattr(quality_cli, "ConfigManager", MagicMock(return_value=config_manager))
    monkeypatch.setattr(quality_cli, "initialize_git_platform", MagicMock(return_value=(git_agent, MagicMock())))
    monkeypatch.setattr(quality_cli, "RepositoryQualityScorer", MagicMock(return_value=scorer))
    monkeypatch.setattr(quality_cli, "RichStageProgress", FakeProgress)
    monkeypatch.setattr(quality_cli, "delete_created_remote_clone", cleanup)

    assert quality_cli.main() == (1 if fails else 0)
    cleanup.assert_called_once_with(args.repository, git_agent.clone_dir, existed_before_clone=False)
