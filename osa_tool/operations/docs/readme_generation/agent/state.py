"""Mutable workflow state for the README generation LangGraph pipeline."""

from __future__ import annotations

from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field

from osa_tool.core.models.event import OperationEvent
from osa_tool.operations.docs.readme_generation.agent.models import (
    RepositoryContext,
    SectionResult,
    SectionSpec,
    TaskIntent,
)


def _merge_dicts(left: dict, right: dict) -> dict:
    """Reducer that merges two dicts (right overwrites overlapping keys)."""
    merged = left.copy()
    merged.update(right)
    return merged


class ReadmeState(BaseModel):
    """Mutable workflow state for the README generation sub-graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # ── Inputs ──
    repo_url: str
    attachment: Optional[str] = None
    user_request: Optional[str] = None

    # ── Collected context (context_collector) ──
    context: Optional[RepositoryContext] = None

    # ── Intent analysis (intent_analyzer) ──
    intent: Optional[TaskIntent] = None

    # ── Section plan (section_planner) ──
    section_plan: list[SectionSpec] = Field(default_factory=list)

    # ── Generated sections — uses a merge reducer so parallel Send writes combine ──
    sections: Annotated[dict[str, SectionResult], _merge_dicts] = Field(default_factory=dict)
    section_errors: Annotated[dict[str, str], _merge_dicts] = Field(default_factory=dict)

    # ── Current section being generated (set per-Send by fan-out) ──
    current_section: Optional[SectionSpec] = None

    # ── Assembly & refinement ──
    readme_draft: Optional[str] = None
    readme_final: Optional[str] = None
    refinement_score: Optional[float] = None
    refinement_issues: list[str] = Field(default_factory=list)
    refinement_cycles: int = 0
    max_refinement_cycles: int = 2

    # ── Output ──
    events: list[OperationEvent] = Field(default_factory=list)
    error: Optional[str] = None
