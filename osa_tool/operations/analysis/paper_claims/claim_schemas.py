from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator

from osa_tool.operations.analysis.paper_claims.models import ClaimCategory, Verifiability


class StrictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SelectedSectionResponse(StrictResponse):
    section_id: str


class ClaimCandidateResponse(StrictResponse):
    claim: str
    original_text: str
    category: ClaimCategory
    value: str | None = None
    verifiability: Verifiability

    @field_validator("claim", "original_text")
    @classmethod
    def require_non_blank_text(cls, value: str) -> str:
        """Reject empty evidence without normalizing valid verbatim text."""
        if not value.strip():
            raise ValueError("must contain non-whitespace text")
        return value
