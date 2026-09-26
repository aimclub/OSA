"""Public data contracts for paper-to-repository analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from osa_tool.operations.analysis.artifacts import ModelProvenance


class StrictModel(BaseModel):
    """Base model that rejects accidental public-contract fields."""

    model_config = ConfigDict(extra="forbid")


class PaperAnalysisRequest(StrictModel):
    """Input accepted by :class:`PaperAnalysisOperation`."""

    repository: str
    output_dir: Path
    paper_path: Path | None = None
    sections_path: Path | None = None
    claims_path: Path | None = None
    paper_claims_prompts_dir: Path | None = None
    include_repository_quality: bool = False
    only_high_medium_verifiability: bool = True
    hide_low_confidence: bool = True

    @model_validator(mode="after")
    def require_exactly_one_claim_source(self) -> "PaperAnalysisRequest":
        provided = sum(item is not None for item in (self.paper_path, self.sections_path, self.claims_path))
        if provided != 1:
            raise ValueError("Provide exactly one of paper_path, sections_path, or claims_path")
        return self


class ClaimSelection(StrictModel):
    """Policies applied before and after claim verification."""

    only_high_medium_verifiability: bool
    allowed_verifiability: list[str] | None = None
    hide_low_confidence: bool


class ClaimVerificationStats(StrictModel):
    """Counts retained so reports do not hide selection effects."""

    source_total: int
    eligible_total: int
    scored_total: int
    excluded_low_verifiability: int
    excluded_invalid_verifiability: int
    hidden_low_confidence: int
    total: int
    implemented: int
    not_implemented: int
    implementation_rate: float
    implementation_rate_pct: int


class ClaimVerificationResult(StrictModel):
    """Claims annotated against the repository and their selection metadata."""

    claims: list[dict[str, Any]] = Field(default_factory=list)
    selection: ClaimSelection
    stats: ClaimVerificationStats
    csv_stats: list[dict[str, Any]] = Field(default_factory=list)


class PaperClaimsSummary(StrictModel):
    """Provenance for the claim input consumed by the verifier."""

    source_kind: Literal["pdf", "sections_json", "claims_json"]
    source_path: Path
    claim_count: int
    model: ModelProvenance = Field(default_factory=ModelProvenance)
    artifacts: dict[str, Path] = Field(default_factory=dict)


class PaperAnalysisArtifacts(StrictModel):
    """Files emitted by one operation run."""

    json_path: Path
    text_path: Path
    paper_claims_report_path: Path
    paper_claims_claims_path: Path
    repository_quality_json_path: Path | None = None
    repository_quality_text_path: Path | None = None
    claim_verification_json_path: Path


class PaperAnalysisMetadata(StrictModel):
    """Both analysis inputs and actual model use across composed stages."""

    source: dict[str, Any]
    models: dict[str, ModelProvenance]


class PaperAnalysisResult(StrictModel):
    """Versioned canonical artifact for paper claims and repository verification."""

    schema_version: Literal["1.0"] = "1.0"
    meta: PaperAnalysisMetadata
    repository_quality: dict[str, Any] | None = None
    paper_claims: PaperClaimsSummary
    claim_verification: ClaimVerificationResult
    artifacts: PaperAnalysisArtifacts
