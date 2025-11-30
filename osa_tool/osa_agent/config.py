from typing import Any, List, Optional

from pydantic import BaseModel, Field


class ToolSpec(BaseModel):
    """Declarative tool representation."""

    name: str
    description: str
    args_schema: Optional[dict] = None
    return_schema: Optional[dict] = None


class PlannerPrompts(BaseModel):
    """
    Holds the text parts for planner prompt.
    Loaded from external prompt storage (TOML/YAML).
    """

    problem_statement: str
    rules: str
    examples: str
    desc_restrictions: str
    additional_hints: Optional[str] = None


class LLMBundle(BaseModel):
    """
    Wraps any LLM connector instance
    """

    name: str
    instance: Any


class OSAAgentConfig(BaseModel):
    """
    High-level agent config.
    Can be constructed from CLI + config file + internal defaults.
    """

    llm: LLMBundle
    visual_llm: Optional[LLMBundle] = None

    # Planner behavior
    max_retries: int = 3
    enable_replanning: bool = True
    enable_memory: bool = True

    # Prompts
    planner_prompts: PlannerPrompts

    # Tools
    tools: List[ToolSpec] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
