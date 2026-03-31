"""Mutable workflow state for the README generation LangGraph pipeline."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from osa_tool.core.models.event import OperationEvent
from osa_tool.operations.docs.readme_generation.agent.models import (
    RepositoryContext,
    SectionResult,
    SectionSpec,
    TaskIntent,
)


def _merge_dicts(left: dict, right: dict) -> dict:
    """Reducer: merge two dicts (right overwrites overlapping keys)."""
    merged = left.copy()
    merged.update(right)
    return merged


class ReadmeState(BaseModel):
    """Full mutable state flowing through the README generation graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Inputs
    repo_url: str
    attachment: str | None = None
    user_request: str | None = None

    # Collected context
    context: RepositoryContext | None = None

    # Intent analysis
    intent: TaskIntent | None = None

    # Section plan
    section_plan: list[SectionSpec] = Field(default_factory=list)

    # Generated sections (merge reducer for parallel Send writes)
    sections: Annotated[dict[str, SectionResult], _merge_dicts] = Field(default_factory=dict)
    section_errors: Annotated[dict[str, str], _merge_dicts] = Field(default_factory=dict)

    # Current section (set per-Send by fan-out)
    current_section: SectionSpec | None = None

    # Assembly & self-eval refinement
    readme_draft: str | None = None
    readme_final: str | None = None
    refinement_score: float | None = None
    refinement_issues: list[str] = Field(default_factory=list)
    refinement_cycles: int = 0
    max_refinement_cycles: int = 2
    sections_to_rerun: list[str] = Field(default_factory=list)
    section_regeneration_hints: dict[str, str] = Field(default_factory=dict)

    # Output
    events: list[OperationEvent] = Field(default_factory=list)
    error: str | None = None
