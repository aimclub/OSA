from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from osa_tool.config.settings import ThesisAnalysisSettings, ThesisPaperClaimsSettings
from osa_tool.operations.analysis.thesis_analysis.models import ThesisAnalysisRequest
from osa_tool.operations.analysis.thesis_analysis.pipeline import ThesisAnalysisOperation


def test_request_requires_exactly_one_claim_source(tmp_path):
    with pytest.raises(ValidationError, match="exactly one"):
        ThesisAnalysisRequest(repository="repo", output_dir=tmp_path)

    with pytest.raises(ValidationError, match="exactly one"):
        ThesisAnalysisRequest(
            repository="repo",
            output_dir=tmp_path,
            paper_path=tmp_path / "paper.pdf",
            claims_path=tmp_path / "claims.json",
        )


@pytest.mark.parametrize(
    ("payload", "expected_claim"),
    [
        ({"claims": [{"claim": "typed"}]}, "typed"),
        ({"result": [{"claim": "legacy"}]}, "legacy"),
        ([{"claim": "bare"}], "bare"),
    ],
)
def test_load_claims_json_accepts_typed_legacy_and_bare(payload, expected_claim, tmp_path):
    path = tmp_path / "claims.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    claims = ThesisAnalysisOperation.load_claims_json(path)

    assert claims == [{"claim": expected_claim}]


def test_operation_reuses_quality_report_and_writes_artifacts(monkeypatch, tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    (repository / "main.py").write_text("print('ok')", encoding="utf-8")
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(json.dumps({"claims": [{"claim": "BERT", "verifiability": "high"}]}), encoding="utf-8")

    quality = {"repo_url": "local/repository", "summary": {"score": 80}}
    quality_scorer = MagicMock()
    quality_scorer.get_quality_report.return_value = quality
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.RepositoryQualityScorer",
        MagicMock(return_value=quality_scorer),
    )

    verifier = MagicMock()
    verifier.verify.return_value = MagicMock(
        stats=MagicMock(
            source_total=1,
            eligible_total=1,
            total=1,
            implemented=1,
            implementation_rate_pct=100,
        )
    )
    verifier.verify.return_value.model_dump.return_value = {
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

    from osa_tool.operations.analysis.thesis_analysis.models import ClaimVerificationResult

    verifier.verify.return_value = ClaimVerificationResult.model_validate(verifier.verify.return_value.model_dump())
    config_manager = MagicMock()
    config_manager.get_thesis_analysis_settings.return_value = ThesisAnalysisSettings()
    git_agent = MagicMock(clone_dir=str(repository))
    operation = ThesisAnalysisOperation(
        config_manager,
        git_agent,
        ThesisAnalysisRequest(repository=str(repository), claims_path=claims_path, output_dir=tmp_path / "out"),
        verifier_factory=lambda _clone_dir, _handler, _settings: verifier,
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.ModelHandlerFactory.build",
        MagicMock(return_value=MagicMock()),
    )

    progress: list[tuple[str, float]] = []
    result = operation.run(on_progress=lambda message, fraction: progress.append((message, fraction)))

    quality_scorer.get_quality_report.assert_called_once_with()
    verifier.verify.assert_called_once()
    assert result.repository_quality == quality
    assert result.artifacts.json_path.is_file()
    assert result.artifacts.text_path.read_text(encoding="utf-8").endswith("\n")
    saved = json.loads(result.artifacts.json_path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == "1.0"
    assert saved["repository_quality"]["summary"]["score"] == 80
    assert progress[0] == ("Repository quality scoring", 0.0)
    assert progress[-1] == ("Writing canonical artifacts", 1.0)
    assert any(message == "Claim verification" and fraction == 0.95 for message, fraction in progress)


def test_pdf_input_preserves_optional_pipeline_failure(monkeypatch, tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    quality_scorer = MagicMock()
    quality_scorer.get_quality_report.return_value = {"repo_url": "local/repository", "summary": {"score": 0}}
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.RepositoryQualityScorer",
        MagicMock(return_value=quality_scorer),
    )

    def unavailable_pipeline(_handler):
        raise RuntimeError('Install it with: pip install "osa_tool[paper-claims]".')

    operation = ThesisAnalysisOperation(
        MagicMock(),
        MagicMock(clone_dir=str(repository)),
        ThesisAnalysisRequest(
            repository=str(repository), paper_path=tmp_path / "paper.pdf", output_dir=tmp_path / "out"
        ),
        paper_pipeline_factory=unavailable_pipeline,
    )
    operation._config_manager.get_thesis_analysis_settings.return_value = ThesisAnalysisSettings()
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.ModelHandlerFactory.build",
        MagicMock(return_value=MagicMock()),
    )

    with pytest.raises(RuntimeError, match="paper-claims"):
        operation.run()

    assert not (tmp_path / "out" / "thesis_analysis.json").exists()
    assert not (tmp_path / "out" / "thesis_analysis.txt").exists()


def test_operation_rejects_output_inside_the_repository_before_scoring(monkeypatch, tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(json.dumps([]), encoding="utf-8")
    quality_scorer = MagicMock()
    quality_scorer_class = MagicMock(return_value=quality_scorer)
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.RepositoryQualityScorer",
        quality_scorer_class,
    )
    config_manager = MagicMock()
    config_manager.get_thesis_analysis_settings.return_value = ThesisAnalysisSettings()
    output_dir = repository / "thesis_analysis"
    operation = ThesisAnalysisOperation(
        config_manager,
        MagicMock(clone_dir=str(repository)),
        ThesisAnalysisRequest(repository=str(repository), claims_path=claims_path, output_dir=output_dir),
    )

    with pytest.raises(ValueError, match="outside the analyzed repository"):
        operation.run()

    quality_scorer_class.assert_not_called()
    assert not output_dir.exists()


def test_operation_rejects_symlink_output_resolving_inside_the_repository(monkeypatch, tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    internal_output_dir = repository / "thesis_analysis"
    internal_output_dir.mkdir()
    output_link = tmp_path / "analysis-link"
    output_link.symlink_to(internal_output_dir, target_is_directory=True)
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(json.dumps([]), encoding="utf-8")
    config_manager = MagicMock()
    config_manager.get_thesis_analysis_settings.return_value = ThesisAnalysisSettings()
    quality_scorer_class = MagicMock()
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.RepositoryQualityScorer",
        quality_scorer_class,
    )
    operation = ThesisAnalysisOperation(
        config_manager,
        MagicMock(clone_dir=str(repository)),
        ThesisAnalysisRequest(repository=str(repository), claims_path=claims_path, output_dir=output_link),
    )

    with pytest.raises(ValueError, match="outside the analyzed repository"):
        operation.run()

    quality_scorer_class.assert_not_called()


def test_operation_does_not_create_external_output_when_scoring_fails(monkeypatch, tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    claims_path = tmp_path / "claims.json"
    claims_path.write_text(json.dumps([]), encoding="utf-8")
    quality_scorer = MagicMock()
    quality_scorer.get_quality_report.side_effect = RuntimeError("scoring failed")
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.RepositoryQualityScorer",
        MagicMock(return_value=quality_scorer),
    )
    config_manager = MagicMock()
    config_manager.get_thesis_analysis_settings.return_value = ThesisAnalysisSettings()
    output_dir = tmp_path / "analysis"
    operation = ThesisAnalysisOperation(
        config_manager,
        MagicMock(clone_dir=str(repository)),
        ThesisAnalysisRequest(repository=str(repository), claims_path=claims_path, output_dir=output_dir),
    )

    with pytest.raises(RuntimeError, match="scoring failed"):
        operation.run()

    assert not output_dir.exists()


def test_pdf_claim_loading_disables_nested_paper_claim_progress(tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    paper_path = tmp_path / "paper.pdf"
    paper_path.write_bytes(b"%PDF-test")
    pipeline = MagicMock()
    pipeline_result = MagicMock()
    pipeline_result.extraction.claims = []
    pipeline.run.return_value = pipeline_result
    pipeline.export.return_value = tmp_path / "analysis" / "paper_claims" / "claims.json"
    operation = ThesisAnalysisOperation(
        MagicMock(),
        MagicMock(clone_dir=str(repository)),
        ThesisAnalysisRequest(repository=str(repository), paper_path=paper_path, output_dir=tmp_path / "analysis"),
        paper_pipeline_factory=lambda _handler: pipeline,
    )
    settings = ThesisPaperClaimsSettings()

    claims, summary = operation._load_claims(tmp_path / "analysis", MagicMock(), settings)

    assert claims == []
    assert summary.source_kind == "pdf"
    pipeline.run.assert_called_once_with(paper_path, settings.to_pipeline_options(), show_progress=False)
