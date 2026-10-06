"""Tests for the focused and main paper-analysis commands."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from osa_tool.config.settings import PaperAnalysisSettings
from osa_tool.tools.paper_analysis import __main__ as paper_main
from osa_tool.tools.paper_analysis import cli


def _args(tmp_path, **overrides):
    values = {
        "repository": "https://github.com/example/project",
        "paper": tmp_path / "paper.pdf",
        "sections_json": None,
        "claims_json": None,
        "paper_claims_prompts_dir": None,
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


def test_focused_cli_prints_only_the_root_json_path(monkeypatch, tmp_path, capsys):
    args = _args(tmp_path)
    parser = MagicMock()
    parser.parse_args.return_value = args
    result = SimpleNamespace(artifacts=SimpleNamespace(json_path=Path("analysis.json")))
    monkeypatch.setattr(paper_main, "build_parser", MagicMock(return_value=parser))
    monkeypatch.setattr(paper_main, "configure_focused_tool_logging", MagicMock())
    monkeypatch.setattr(paper_main, "run_paper_analysis", MagicMock(return_value=result))

    assert paper_main.main() == 0
    assert capsys.readouterr().out == "analysis.json\n"


def test_main_cli_paper_mode_bypasses_scheduler(monkeypatch, tmp_path, capsys):
    from osa_tool import run

    args = _args(tmp_path, paper_analysis=True)
    parser = MagicMock()
    parser.parse_args.return_value = args
    result = SimpleNamespace(artifacts=SimpleNamespace(json_path=Path("analysis.json")))
    monkeypatch.setattr(run, "build_parser_from_yaml", MagicMock(return_value=parser))
    monkeypatch.setattr("osa_tool.tools.focused_cli.configure_focused_tool_logging", MagicMock())
    monkeypatch.setattr("osa_tool.tools.paper_analysis.cli.run_paper_analysis", MagicMock(return_value=result))
    monkeypatch.setattr(run, "ModeScheduler", MagicMock(side_effect=AssertionError("scheduler must not run")))

    assert run.main() == 0
    assert capsys.readouterr().out == "analysis.json\n"


def test_request_accepts_sections_json_and_prompt_overrides(tmp_path):
    config_manager = MagicMock()
    config_manager.get_paper_analysis_settings.return_value = PaperAnalysisSettings(output_dir=tmp_path / "output")
    sections_path = tmp_path / "sections.json"
    prompts_dir = tmp_path / "prompts"

    request = cli.build_request(
        _args(
            tmp_path,
            paper=None,
            sections_json=sections_path,
            paper_claims_prompts_dir=prompts_dir,
        ),
        config_manager,
        clone_dir=tmp_path / "repository",
    )

    assert request.paper_path is None
    assert request.sections_path == sections_path
    assert request.claims_path is None
    assert request.paper_claims_prompts_dir == prompts_dir


@pytest.mark.parametrize(
    "overrides",
    [
        {"paper": Path("paper.pdf"), "sections_json": None, "claims_json": None},
        {"paper": None, "sections_json": Path("sections.json"), "claims_json": None},
        {"paper": None, "sections_json": None, "claims_json": Path("claims.json")},
    ],
)
def test_validate_accepts_each_claim_source(tmp_path, overrides):
    parser = MagicMock()
    args = _args(tmp_path, **overrides)

    cli.validate_paper_analysis_args(parser, args)

    parser.error.assert_not_called()


@pytest.mark.parametrize(
    "overrides",
    [
        {"paper": None, "sections_json": None, "claims_json": None},
        {"paper": Path("paper.pdf"), "sections_json": Path("sections.json"), "claims_json": None},
    ],
)
def test_validate_requires_exactly_one_claim_source(tmp_path, overrides):
    parser = MagicMock()
    parser.error.side_effect = RuntimeError("parser error")
    args = _args(tmp_path, **overrides)

    with pytest.raises(RuntimeError, match="parser error"):
        cli.validate_paper_analysis_args(parser, args)

    parser.error.assert_called_once_with("Provide exactly one of --paper, --sections-json, or --claims-json")
