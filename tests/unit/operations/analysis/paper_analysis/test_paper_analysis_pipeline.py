"""Tests for optional repository-quality scoring in paper analysis."""

from __future__ import annotations

import builtins
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

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


class FakePaperClaimsHandler:
    model_settings = type("Settings", (), {"model": "claim-model"})()

    def __init__(self):
        self.responses = iter(
            [
                '[{"section_id":"s001"}]',
                '[{"claim":"The model uses BERT-base.","original_text":"The model uses BERT-base.",'
                '"category":"model_architecture","value":"BERT-base","verifiability":"high"}]',
                '[{"claim_id":"c0001","claim":"The model uses BERT-base.","contradiction":false}]',
            ]
        )
        self.prompts: list[str] = []
        self.system_messages: list[str | None] = []
        self.successful_models: list[str] = []
        self.last_successful_model: str | None = None
        self.provenance_reset_count = 0

    def reset_model_provenance(self):
        self.provenance_reset_count += 1
        self.successful_models.clear()
        self.last_successful_model = None

    async def async_request(self, prompt, system_message=None, retry_delay=1):
        self.prompts.append(prompt)
        self.system_messages.append(system_message)
        self.last_successful_model = self.model_settings.model
        if self.last_successful_model not in self.successful_models:
            self.successful_models.append(self.last_successful_model)
        return next(self.responses)


def _write_sections_json(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "sections": [
                    {
                        "section_id": "s001",
                        "name": "Method",
                        "text": "The model uses BERT-base.",
                        "heading_meta": {"raw": "2. Method", "level": 1, "numbering": "2"},
                    }
                ],
                "meta": {"producer": "unit-test"},
            }
        ),
        encoding="utf-8",
    )


def test_request_requires_exactly_one_claim_source(tmp_path):
    base = {"repository": "repo", "output_dir": tmp_path / "analysis"}

    request = PaperAnalysisRequest(**base, sections_path=tmp_path / "sections.json")

    assert request.sections_path == tmp_path / "sections.json"
    with pytest.raises(ValidationError, match="Provide exactly one"):
        PaperAnalysisRequest(**base)
    with pytest.raises(ValidationError, match="Provide exactly one"):
        PaperAnalysisRequest(
            **base,
            paper_path=tmp_path / "paper.pdf",
            sections_path=tmp_path / "sections.json",
        )


def test_sections_path_analysis_exports_claims_and_never_imports_pdf_stack(monkeypatch, tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "main.py").write_text("print('ok')", encoding="utf-8")
    sections_path = tmp_path / "sections.json"
    _write_sections_json(sections_path)
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    (prompts_dir / "paper_claims.toml").write_text(
        '[prompts]\nsection_filter_system = "custom section filter system"\n',
        encoding="utf-8",
    )
    handler = FakePaperClaimsHandler()
    model_factory = MagicMock(side_effect=[handler, MagicMock()])
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_analysis.pipeline.ModelHandlerFactory.build",
        model_factory,
    )

    original_import = builtins.__import__
    blocked_modules = {
        "osa_tool.operations.analysis.paper_claims.pdf_splitter",
        "osa_tool.operations.analysis.paper_claims.marker_converter",
        "osa_tool.operations.analysis.paper_claims.section_parser",
    }

    def reject_pdf_stack_imports(name, *args, **kwargs):
        if any(name == blocked or name.startswith(f"{blocked}.") for blocked in blocked_modules):
            raise AssertionError(f"sections_json path must not import {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_pdf_stack_imports)
    verifier = MagicMock()
    verifier.verify.return_value = _verification_result()
    verifier.export.side_effect = _write_fake_verification_report
    verifier.get_model_provenance.return_value = ModelProvenance(configured="verify", used=["verify"])
    config_manager = MagicMock()
    config_manager.get_paper_analysis_settings.return_value = PaperAnalysisSettings()
    request = PaperAnalysisRequest(
        repository=str(repository),
        sections_path=sections_path,
        paper_claims_prompts_dir=prompts_dir,
        output_dir=tmp_path / "analysis",
    )

    result = PaperAnalysisOperation(
        config_manager,
        MagicMock(clone_dir=str(repository)),
        request,
        verifier_factory=lambda _clone_dir, _handler, _settings: verifier,
    ).run()

    assert result.paper_claims.source_kind == "sections_json"
    assert result.paper_claims.claim_count == 1
    assert result.paper_claims.model == ModelProvenance(configured="claim-model", used=["claim-model"])
    assert result.meta.source["paper"] == {"kind": "sections_json", "path": str(sections_path)}
    assert result.artifacts.paper_claims_claims_path.is_file()
    assert result.artifacts.paper_claims_report_path.is_file()
    assert (tmp_path / "analysis" / "paper_claims" / "sections.json").is_file()
    assert not (tmp_path / "analysis" / "paper_claims" / "document.md").exists()
    report = json.loads(result.artifacts.paper_claims_report_path.read_text(encoding="utf-8"))
    assert report["meta"]["source"]["paper"] == {"kind": "sections_json", "path": str(sections_path)}
    assert report["meta"]["source"]["upstream"] == {"producer": "unit-test"}
    assert handler.system_messages[0] == "custom section filter system"
    assert handler.provenance_reset_count == 1
    assert model_factory.call_count == 2
