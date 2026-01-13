from typing import List, Dict, Any

from pydantic import BaseModel, RootModel


class PlannerDecision(BaseModel):
    """Output of Planner agent."""

    operations: List[str]
    reasoning: str


class ArgumentDetectionResponse(RootModel):
    """Response structure for detected arguments from the LLM."""

    root: Dict[str, Dict[str, Any]]
