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
    max_refinement_cycles: int = 3
    sections_to_rerun: list[str] = Field(default_factory=list)
    section_regeneration_hints: dict[str, str] = Field(default_factory=dict)

    # Output
    events: list[OperationEvent] = Field(default_factory=list)
    error: str | None = None

    def __str__(self) -> str:
        ctx = self.context
        intent = self.intent
        plan_summary = ", ".join(f"{s.name}({s.strategy})" for s in self.section_plan)
        sections_done = list(self.sections.keys())
        errors = list(self.section_errors.keys())

        return (
            f"ReadmeState(\n"
            f"  repo_url={self.repo_url},\n"
            f"  attachment={'yes' if self.attachment else 'no'},\n"
            f"  user_request={self.user_request!r},\n"
            f"  context={'collected' if ctx else 'not collected'},\n"
            f"  context.has_tests={ctx.has_tests if ctx else 'N/A'},\n"
            f"  context.pdf={'yes' if ctx and ctx.pdf_content else 'no'},\n"
            f"  intent={intent.task_type if intent else None}/{intent.scope if intent else None},\n"
            f"  incorporate_paper={intent.incorporate_paper if intent else False},\n"
            f"  section_plan=[{plan_summary}],\n"
            f"  sections_generated={sections_done},\n"
            f"  section_errors={errors},\n"
            f"  current_section={self.current_section.name if self.current_section else None},\n"
            f"  readme_draft={'%d chars' % len(self.readme_draft) if self.readme_draft else None},\n"
            f"  readme_final={'%d chars' % len(self.readme_final) if self.readme_final else None},\n"
            f"  refinement_cycles={self.refinement_cycles}/{self.max_refinement_cycles},\n"
            f"  refinement_score={self.refinement_score},\n"
            f"  sections_to_rerun={self.sections_to_rerun},\n"
            f"  events={len(self.events)},\n"
            f"  error={self.error}\n"
            f")"
        )
