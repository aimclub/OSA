from typing import Any, Optional, List

from pydantic import BaseModel, Field


class ParameterUpdate(BaseModel):
    """One parameter to set/update."""

    name: str = Field(..., description="Parameter name to set or update")
    value: Any = Field(..., description="Value for the parameter; JSON-serializable")
    type: Optional[str] = Field(None, description="Type of parameter: flag, str, list, etc.")
    choices: Optional[List[Any]] = Field(None, description="List of valid choices if applicable")
    source: Optional[str] = Field(None, description="Agent that produced this parameter")


class PlannerResponse(BaseModel):
    """LLM output for the planner node. Must be valid JSON returned by the LLM."""

    thoughts: Optional[str] = Field(
        default=None, description="Chain-of-thought-like internal reasoning. Not exposed to user."
    )
    action: str = Field(..., description="Next agent action: update_parameters, ask_user, final, or none.")
    parameters: List[ParameterUpdate] = Field(
        default_factory=list, description="List of parameters that planner wants to modify or set."
    )
    final_answer: Optional[str] = Field(default=None, description="Optional final response if action='final'.")
