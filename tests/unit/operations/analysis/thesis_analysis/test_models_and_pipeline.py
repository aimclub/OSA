from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

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
        "osa_tool.operations.analysis.thesis_analysis.pipeline.VkrScorer",
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
    git_agent = MagicMock(clone_dir=str(repository))
    operation = ThesisAnalysisOperation(
        config_manager,
        git_agent,
        ThesisAnalysisRequest(repository=str(repository), claims_path=claims_path, output_dir=tmp_path / "out"),
        verifier_factory=lambda _clone_dir, _handler: verifier,
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.ModelHandlerFactory.build",
        MagicMock(return_value=MagicMock()),
    )

    result = operation.run()

    quality_scorer.get_quality_report.assert_called_once_with()
    verifier.verify.assert_called_once()
    assert result.repository_quality == quality
    assert result.artifacts.json_path.is_file()
    assert result.artifacts.text_path.read_text(encoding="utf-8").endswith("\n")
    saved = json.loads(result.artifacts.json_path.read_text(encoding="utf-8"))
    assert saved["schema_version"] == "1.0"
    assert saved["repository_quality"]["summary"]["score"] == 80


def test_pdf_input_preserves_optional_pipeline_failure(monkeypatch, tmp_path):
    repository = tmp_path / "repository"
    repository.mkdir()
    quality_scorer = MagicMock()
    quality_scorer.get_quality_report.return_value = {"repo_url": "local/repository", "summary": {"score": 0}}
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.VkrScorer",
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
    monkeypatch.setattr(
        "osa_tool.operations.analysis.thesis_analysis.pipeline.ModelHandlerFactory.build",
        MagicMock(return_value=MagicMock()),
    )

    with pytest.raises(RuntimeError, match="paper-claims"):
        operation.run()
