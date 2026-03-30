"""README-specific Pydantic schemas for structured LLM outputs."""

from pydantic import BaseModel, ConfigDict, Field


class KeyFilesLLMOutput(BaseModel):
    """LLM response listing key repository files to read."""

    model_config = ConfigDict(extra="ignore")
    key_files: list[str] = Field(default_factory=list)


class ReadmeSelfEvalLLMOutput(BaseModel):
    """LLM self-evaluation of a generated README."""

    model_config = ConfigDict(extra="ignore")

    score: float = 0
    issues: list[str] = Field(default_factory=list)
    should_stop: bool = False
