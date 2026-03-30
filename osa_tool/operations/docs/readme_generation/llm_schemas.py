"""README-specific Pydantic schemas for structured LLM outputs."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class CoreFeatureItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    feature_name: str = ""
    feature_description: str = ""
    is_critical: bool = False


class CoreFeaturesLLMOutput(BaseModel):
    """Canonical core-features payload with compatibility normalization."""
    model_config = ConfigDict(extra="ignore")
    features: list[CoreFeatureItem] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def normalize_payload(cls, value: Any) -> Any:
        # Backward compatibility: bare list -> {"features": [...]}
        if isinstance(value, list):
            return {"features": value}
        if isinstance(value, dict):
            features = value.get("features")
            if isinstance(features, list):
                return value
            # Graceful handling for a single feature object.
            if "feature_name" in value and "feature_description" in value:
                return {"features": [value]}
        return value


class ReadmeSelfEvalLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    score: float = 0
    issues: list[str] = Field(default_factory=list)
    should_stop: bool = False
