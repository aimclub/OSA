from __future__ import annotations

from pydantic import BaseModel, ConfigDict

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
