"""Tests for focused and top-level thesis-analysis CLI entry points."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from osa_tool.config.settings import ThesisAnalysisSettings
from osa_tool.tools.thesis_analysis import __main__ as thesis_main
from osa_tool.tools.thesis_analysis import cli


def _args(tmp_path, **overrides):
    values = {
        "repository": "https://github.com/example/thesis",
        "paper": tmp_path / "paper.pdf",
        "claims_json": None,
        "thesis_output_dir": None,
        "only_high_medium_verifiability": None,
        "hide_low_confidence": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_request_uses_config_defaults_and_explicit_cli_overrides(tmp_path):
    settings = ThesisAnalysisSettings(
        output_dir=tmp_path / "configured-output",
        only_high_medium_verifiability=False,
        hide_low_confidence=False,
    )
    config_manager = MagicMock()
    config_manager.get_thesis_analysis_settings.return_value = settings

    request = cli.build_request(_args(tmp_path), config_manager)
    override_request = cli.build_request(
        _args(
            tmp_path,
            thesis_output_dir=tmp_path / "cli-output",
            only_high_medium_verifiability=True,
            hide_low_confidence=True,
        ),
        config_manager,
    )

    assert request.output_dir == settings.output_dir
    assert request.only_high_medium_verifiability is False
    assert request.hide_low_confidence is False
    assert override_request.output_dir == tmp_path / "cli-output"
    assert override_request.only_high_medium_verifiability is True
    assert override_request.hide_low_confidence is True


def test_request_places_a_relative_default_output_beside_the_clone(tmp_path):
    clone_dir = tmp_path / "repository"
    config_manager = MagicMock()
    config_manager.get_thesis_analysis_settings.return_value = ThesisAnalysisSettings(output_dir=Path("analysis"))

    request = cli.build_request(_args(tmp_path), config_manager, clone_dir=clone_dir)

    assert request.output_dir == tmp_path / "analysis"


def test_shared_runner_clones_once_and_forwards_progress(monkeypatch, tmp_path):
    args = _args(tmp_path)
    config_manager = MagicMock()
    config_manager.get_thesis_analysis_settings.return_value = ThesisAnalysisSettings(output_dir=tmp_path / "output")
    git_agent = MagicMock(clone_dir=str(tmp_path / "clone"))
    operation = MagicMock()
    operation.run.side_effect = lambda *, on_progress: on_progress("Writing canonical artifacts", 1.0) or "result"
    updates: list[tuple[str, float]] = []

    class FakeProgress:
        def __init__(self, _description):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def update(self, description, fraction):
            updates.append((description, fraction))

    monkeypatch.setattr(cli, "RichStageProgress", FakeProgress)

    result = cli.run_thesis_analysis(
        args,
        config_manager_factory=lambda _args: config_manager,
        git_initializer=lambda _args, _config: (git_agent, MagicMock()),
        operation_factory=lambda _config, _git, _request: operation,
    )

    assert result == "result"
    git_agent.clone_repository.assert_called_once_with()
    assert updates == [
        ("Cloning repository", 0.0),
        ("Repository cloned", 0.10),
        ("Writing canonical artifacts", 1.0),
    ]


def test_focused_cli_delegates_to_shared_runner(monkeypatch, tmp_path, capsys):
    args = _args(tmp_path)
    parser = MagicMock()
    parser.parse_args.return_value = args
    result = SimpleNamespace(artifacts=SimpleNamespace(json_path=Path("analysis.json")))

    monkeypatch.setattr(thesis_main, "build_parser", MagicMock(return_value=parser))
    monkeypatch.setattr(thesis_main, "configure_focused_tool_logging", MagicMock())
    monkeypatch.setattr(thesis_main, "run_thesis_analysis", MagicMock(return_value=result))

    assert thesis_main.main() == 0
    thesis_main.run_thesis_analysis.assert_called_once_with(args)
    assert capsys.readouterr().out == "analysis.json\n"


def test_main_cli_thesis_mode_bypasses_scheduler_and_legacy_workflows(monkeypatch, tmp_path, capsys):
    from osa_tool import run

    args = _args(tmp_path, thesis_analysis=True)
    parser = MagicMock()
    parser.parse_args.return_value = args
    result = SimpleNamespace(artifacts=SimpleNamespace(json_path=Path("analysis.json")))

    monkeypatch.setattr(run, "build_parser_from_yaml", MagicMock(return_value=parser))
    monkeypatch.setattr("osa_tool.tools.thesis_analysis.cli.configure_focused_tool_logging", MagicMock())
    monkeypatch.setattr("osa_tool.tools.thesis_analysis.cli.run_thesis_analysis", MagicMock(return_value=result))
    monkeypatch.setattr(run, "ModeScheduler", MagicMock(side_effect=AssertionError("scheduler must not run")))

    assert run.main() == 0
    assert capsys.readouterr().out == "analysis.json\n"
