"""README-specific Pydantic schemas for structured LLM outputs."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KeyFilesLLMOutput(BaseModel):
    """LLM response listing key repository files to read."""

    model_config = ConfigDict(extra="ignore")
    key_files: list[str] = Field(default_factory=list)


class SectionPlanLLMOutput(BaseModel):
    """LLM returns only internal section names; catalog supplies priority, prompts, and context keys."""

    model_config = ConfigDict(extra="ignore")
    section_names: list[str] = Field(default_factory=list)


SelfEvalSeverity = Literal["blocker", "major", "minor"]


class SelfEvalIssue(BaseModel):
    """One README defect from self-eval (severity + short description)."""

    model_config = ConfigDict(extra="ignore")

    severity: SelfEvalSeverity
    description: str = Field(default="")

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, value: object) -> object:
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("blocker", "major", "minor"):
                return v
        return value

    @field_validator("description", mode="before")
    @classmethod
    def _strip_description(cls, value: object) -> object:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        return value


class ReadmeSelfEvalLLMOutput(BaseModel):
    """LLM self-evaluation of a generated README."""

    model_config = ConfigDict(extra="ignore")

    issues: list[SelfEvalIssue] = Field(default_factory=list)

    @field_validator("issues", mode="before")
    @classmethod
    def _coerce_legacy_string_issues(cls, value: object) -> object:
        """Accept pre-structured list[str] issues as major-severity items (backward compatible)."""
        if not isinstance(value, list):
            return value
        out: list[object] = []
        for item in value:
            if isinstance(item, str):
                text = item.strip()
                if text:
                    out.append({"severity": "major", "description": text})
            else:
                out.append(item)
        return out

    should_stop: bool = False
    sections_to_rerun: list[str] = Field(default_factory=list)
    section_feedback: dict[str, str] | None = None
    quality_notes: str | None = None
