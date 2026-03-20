from typing import Optional, Literal

from pydantic import BaseModel, Field


class ReviewerDecision(BaseModel):
    """
    Output of the ReviewerAgent after analyzing user feedback.
    """


    requires_new_intent: bool = Field(
        default=False, description="Whether user feedback implies a completely new intent."
    )

    requires_new_task_scope: bool = Field(
        default=False, description="Whether user feedback requires redefining or expanding task_scope."
    )

    new_intent: Optional[Literal["new_task", "feedback", "unknown"]] = Field(
        default=None, description="New intent extracted from user feedback (must match IntentDecision.intent)."
    )

    new_task_scope: Optional[Literal["none", "analysis", "docs", "codebase", "full_repo"]] = Field(
        default=None,
        description="Reconstructed task scope aligned with new intent (must match IntentDecision.task_scope).",
    )

    reviewer_summary: Optional[str] = Field(
        default=None, description="Short explanation of the decision for debug/logging."
    )
