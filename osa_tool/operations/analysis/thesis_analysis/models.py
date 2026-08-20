"""Public data contracts for thesis repository analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    """Base model that rejects accidental public-contract fields."""

    model_config = ConfigDict(extra="forbid")


class ThesisAnalysisRequest(StrictModel):
    """Input accepted by :class:`ThesisAnalysisOperation`."""

    repository: str
    output_dir: Path
    paper_path: Path | None = None
    claims_path: Path | None = None
    only_high_medium_verifiability: bool = True
    hide_low_confidence: bool = True

    @model_validator(mode="after")
    def require_exactly_one_claim_source(self) -> "ThesisAnalysisRequest":
        if (self.paper_path is None) == (self.claims_path is None):
            raise ValueError("Provide exactly one of paper_path or claims_path")
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

    source_kind: Literal["pdf", "claims_json"]
    source_path: Path
    claim_count: int
    artifacts: dict[str, Path] = Field(default_factory=dict)


class ThesisAnalysisArtifacts(StrictModel):
    """Files emitted by one operation run."""

    json_path: Path
    text_path: Path


class ThesisAnalysisResult(StrictModel):
    """Versioned canonical artifact for the complete thesis-analysis flow."""

    schema_version: Literal["1.0"] = "1.0"
    repository_quality: dict[str, Any]
    paper_claims: PaperClaimsSummary
    claim_verification: ClaimVerificationResult
    artifacts: ThesisAnalysisArtifacts
