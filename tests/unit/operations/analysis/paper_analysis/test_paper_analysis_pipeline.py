"""Tests for optional repository-quality scoring in paper analysis."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from osa_tool.config.settings import PaperAnalysisSettings
from osa_tool.operations.analysis.artifacts import ModelProvenance
from osa_tool.operations.analysis.paper_analysis import (
    ClaimVerificationResult,
    PaperAnalysisOperation,
    PaperAnalysisRequest,
)


def _verification_result() -> ClaimVerificationResult:
    return ClaimVerificationResult.model_validate(
        {
            "claims": [],
            "selection": {
                "only_high_medium_verifiability": True,
                "allowed_verifiability": ["high", "medium"],
                "hide_low_confidence": True,
            },
            "stats": {
                "source_total": 1,
                "eligible_total": 1,
                "scored_total": 1,
                "excluded_low_verifiability": 0,
                "excluded_invalid_verifiability": 0,
                "hidden_low_confidence": 0,
                "total": 1,
                "implemented": 1,
                "not_implemented": 0,
                "implementation_rate": 1.0,
                "implementation_rate_pct": 100,
            },
            "csv_stats": [],
        }
    )


def _write_fake_verification_report(_result, destination, *, source):
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / "report.json"
    report_path.write_text(json.dumps({"meta": {"source": source}}), encoding="utf-8")
    return report_path


def _write_fake_quality_report(_report, destination, *, source):
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "report.json"
    text_path = destination / "report.txt"
    json_path.write_text(json.dumps({"meta": {"source": source}}), encoding="utf-8")
    text_path.write_text("quality", encoding="utf-8")
    return json_path, text_path


def _operation(tmp_path, *, include_repository_quality: bool, verifier, config_manager):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "main.py").write_text("print('ok')", encoding="utf-8")
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(json.dumps({"claims": [{"claim": "BERT", "verifiability": "high"}]}), encoding="utf-8")
    request = PaperAnalysisRequest(
        repository=str(repository),
        claims_path=claims_path,
        output_dir=tmp_path / "analysis",
        include_repository_quality=include_repository_quality,
    )
    return PaperAnalysisOperation(
        config_manager,
        MagicMock(clone_dir=str(repository)),
        request,
        verifier_factory=lambda _clone_dir, _handler, _settings: verifier,
    )


def test_default_run_skips_quality_model_and_artifacts(monkeypatch, tmp_path):
    verifier = MagicMock()
    verifier.verify.return_value = _verification_result()
    verifier.export.side_effect = _write_fake_verification_report
    verifier.get_model_provenance.return_value = ModelProvenance(configured="verify", used=["verify"])
    config_manager = MagicMock()
    config_manager.get_paper_analysis_settings.return_value = PaperAnalysisSettings()
    model_factory = MagicMock(return_value=MagicMock())
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_analysis.pipeline.ModelHandlerFactory.build",
        model_factory,
    )

    result = _operation(
        tmp_path,
        include_repository_quality=False,
        verifier=verifier,
        config_manager=config_manager,
    ).run()

    assert result.repository_quality is None
    assert result.artifacts.repository_quality_json_path is None
    assert result.artifacts.repository_quality_text_path is None
    assert not (tmp_path / "analysis" / "repository_quality").exists()
    model_factory.assert_called_once()
    config_manager.get_model_settings.assert_called_once_with("paper_verification")
    payload = json.loads(result.artifacts.json_path.read_text(encoding="utf-8"))
    assert payload["repository_quality"] is None
    assert set(payload["meta"]["models"]) == {"paper_claims", "paper_verification"}


def test_enabled_run_exports_the_existing_quality_report(monkeypatch, tmp_path):
    from osa_tool.operations.analysis.repository_quality import repository_quality_scorer

    verifier = MagicMock()
    verifier.verify.return_value = _verification_result()
    verifier.export.side_effect = _write_fake_verification_report
    verifier.get_model_provenance.return_value = ModelProvenance(configured="verify", used=["verify"])
    quality = {"repo_url": "local/repository", "summary": {"score": 80}}
    scorer = MagicMock()
    scorer.get_quality_report.return_value = quality
    scorer.export_report.side_effect = _write_fake_quality_report
    scorer.get_model_provenance.return_value = ModelProvenance(configured="quality", used=["quality"])
    scorer_factory = MagicMock(return_value=scorer)
    monkeypatch.setattr(repository_quality_scorer, "RepositoryQualityScorer", scorer_factory)
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_analysis.pipeline.ModelHandlerFactory.build",
        MagicMock(return_value=MagicMock()),
    )
    config_manager = MagicMock()
    config_manager.get_paper_analysis_settings.return_value = PaperAnalysisSettings()

    result = _operation(
        tmp_path,
        include_repository_quality=True,
        verifier=verifier,
        config_manager=config_manager,
    ).run()

    scorer_factory.assert_called_once()
    assert result.repository_quality == quality
    assert result.artifacts.repository_quality_json_path.is_file()
    assert result.artifacts.repository_quality_text_path.is_file()
    assert "repository_quality" in result.meta.models
    assert "Repository quality score: 80/100" in result.artifacts.text_path.read_text(encoding="utf-8")


def test_invalid_claim_input_fails_before_optional_quality_scoring(monkeypatch, tmp_path):
    from osa_tool.operations.analysis.repository_quality import repository_quality_scorer

    repository = tmp_path / "repository"
    repository.mkdir()
    scorer_factory = MagicMock()
    model_factory = MagicMock()
    monkeypatch.setattr(repository_quality_scorer, "RepositoryQualityScorer", scorer_factory)
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_analysis.pipeline.ModelHandlerFactory.build",
        model_factory,
    )
    config_manager = MagicMock()
    config_manager.get_paper_analysis_settings.return_value = PaperAnalysisSettings()
    operation = PaperAnalysisOperation(
        config_manager,
        MagicMock(clone_dir=str(repository)),
        PaperAnalysisRequest(
            repository=str(repository),
            claims_path=tmp_path / "missing.json",
            output_dir=tmp_path / "analysis",
            include_repository_quality=True,
        ),
    )

    with pytest.raises(FileNotFoundError):
        operation.run()

    scorer_factory.assert_not_called()
    model_factory.assert_not_called()


@pytest.mark.parametrize(
    ("payload", "claim"),
    [
        ({"claims": [{"claim": "typed"}]}, "typed"),
        ({"result": [{"claim": "legacy"}]}, "legacy"),
        ([{"claim": "bare"}], "bare"),
    ],
)
def test_load_claims_json_accepts_resumable_formats(tmp_path, payload, claim):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    assert PaperAnalysisOperation.load_claims_json(path) == [{"claim": claim}]
