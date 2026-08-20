"""Regression tests for the quality-only VKR scorer boundary."""

from __future__ import annotations

import inspect
import json
from pathlib import Path
from unittest.mock import MagicMock

from osa_tool.operations.analysis.vkr_scoring.vkr_scorer import VkrScorer


def test_vkr_scorer_is_quality_only_and_preserves_quality_report(monkeypatch, tmp_path):
    config_manager = MagicMock()
    config_manager.config.git.repository = "https://github.com/example/thesis"
    config_manager.get_model_settings.return_value = MagicMock()
    git_agent = MagicMock(clone_dir=str(tmp_path), repo=MagicMock())

    checker = MagicMock()
    checker.run_all.return_value = {
        "repo_type": {"value": "app"},
        "readme": {"present": True, "meaningful": True},
    }
    monkeypatch.setattr(
        "osa_tool.operations.analysis.vkr_scoring.vkr_scorer.ModelHandlerFactory.build",
        MagicMock(return_value=MagicMock()),
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.vkr_scoring.vkr_scorer.build_file_tree",
        MagicMock(return_value=(["README.md"], ["README.md"])),
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.vkr_scoring.vkr_scorer.VkrChecker",
        MagicMock(return_value=checker),
    )

    assert "paper_path" not in inspect.signature(VkrScorer).parameters
    scorer = VkrScorer(config_manager, git_agent, output_dir=str(tmp_path / "out"))

    quality = scorer.get_quality_report()
    run_result = scorer.run()

    assert quality["summary"]["score"] == 25
    assert "claims_analysis" not in quality
    saved_report = json.loads(Path(run_result["result"]["json_path"]).read_text(encoding="utf-8"))
    assert saved_report["checks"] == quality["checks"]
    assert saved_report["summary"] == quality["summary"]
    assert "claims_analysis" not in saved_report
