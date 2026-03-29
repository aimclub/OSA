"""README-specific Pydantic schemas for structured LLM outputs."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel, field_validator


class KeyFilesLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    key_files: list[str] = Field(default_factory=list)


class DiagnosisLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    generation_mode: str = "full_regen"
    target_sections: list[str] = Field(default_factory=list)
    generation_plan: str = ""

    @field_validator("generation_mode", mode="after")
    @classmethod
    def normalize_generation_mode(cls, v: str) -> str:
        if v in ("full_regen", "targeted"):
            return v
        return "full_regen"


class CoreFeaturesLLMOutput(RootModel[dict[str, Any]]):
    """Full JSON object for the core-features prompt (arbitrary keys)."""

    pass


class ReadmeSelfEvalLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    score: float = 0
    issues: list[str] = Field(default_factory=list)
    should_stop: bool = False
