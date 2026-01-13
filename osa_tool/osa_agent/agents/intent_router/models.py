from typing import Literal, Optional

from pydantic import BaseModel


class IntentDecision(BaseModel):
    """Output of IntentRouter agent."""

    intent: Literal["new_task", "feedback", "unknown"]
    task_scope: Optional[
        Literal[
            "none",
            "analysis",  # only analysis, reports
            "docs",  # documentation (README, LICENSE, community, about)
            "codebase",  # code + structure + files
            "full_repo",  # all
        ]
    ] = None
    confidence: float
