"""Dynamically plan which README sections to generate based on intent and repository context."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.models import SectionSpec
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError


class _PlannedSection(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str
    title: str
    description: str = ""
    prompt_context_keys: list[str] = Field(default_factory=list)


class SectionPlanLLMOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    sections: list[_PlannedSection] = Field(default_factory=list)


DETERMINISTIC_SECTIONS: list[SectionSpec] = [
    SectionSpec(name="header", title="Header", strategy="deterministic", priority=0),
    SectionSpec(name="table_of_contents", title="Table of Contents", strategy="deterministic", priority=5),
    SectionSpec(name="installation", title="Installation", strategy="deterministic", priority=30),
    SectionSpec(name="examples", title="Examples", strategy="deterministic", priority=60),
    SectionSpec(name="documentation", title="Documentation", strategy="deterministic", priority=65),
    SectionSpec(name="contributing", title="Contributing", strategy="deterministic", priority=80),
    SectionSpec(name="license", title="License", strategy="deterministic", priority=90),
    SectionSpec(name="citation", title="Citation", strategy="deterministic", priority=95),
]

_DETERMINISTIC_NAMES = frozenset(s.name for s in DETERMINISTIC_SECTIONS)

# Keep LLM section count small; the prompt also asks for brevity.
_MAX_LLM_SECTIONS = 7

_DISCOURAGED_BY_DEFAULT = frozenset(
    {
        "faq",
        "troubleshooting",
        "changelog",
        "acknowledgments",
        "acknowledgements",
    }
)


def _user_wants_discouraged(user_request: str | None, name: str) -> bool:
    if not user_request:
        return False
    ur = user_request.lower()
    if name in ("faq",):
        return "faq" in ur
    if name in ("troubleshooting",):
        return "troubleshoot" in ur or "troubleshooting" in ur
    if name in ("changelog",):
        return "changelog" in ur
    if name in ("acknowledgments", "acknowledgements"):
        return "acknowledgment" in ur or "acknowledgement" in ur
    return False


def _normalize_llm_sections(sections: list[_PlannedSection], user_request: str | None) -> list[_PlannedSection]:
    """Drop discouraged sections, collapse overlap, and cap count."""
    names = {s.name for s in sections}
    out: list[_PlannedSection] = []

    for sec in sections:
        if sec.name in _DISCOURAGED_BY_DEFAULT and not _user_wants_discouraged(user_request, sec.name):
            continue
        if sec.name == "usage" and "getting_started" in names:
            continue
        if sec.name == "notebook_usage" and "getting_started" in names:
            continue
        if sec.name == "data_requirements" and "getting_started" in names:
            continue
        out.append(sec)

    if len(out) > _MAX_LLM_SECTIONS:
        logger.info(
            "[SectionPlanner] Truncating LLM section list from %d to %d (max).",
            len(out),
            _MAX_LLM_SECTIONS,
        )
        out = out[:_MAX_LLM_SECTIONS]

    return out


def _extract_existing_headings(readme: str) -> str:
    """Pull markdown headings from existing README for the planner's context."""
    if not readme:
        return "None"
    headings = re.findall(r"^#{1,3}\s+(.+)$", readme, re.MULTILINE)
    return "\n".join(f"- {h}" for h in headings) if headings else "None"


def _build_llm_plan(state: ReadmeState, context: ReadmeContext) -> list[_PlannedSection]:
    """Ask the LLM to propose the LLM-generated section list."""
    ctx = state.context
    intent = state.intent

    existing_sections = _extract_existing_headings(ctx.existing_readme if ctx else "")

    raw = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_agent.section_planning"),
            task_type=intent.task_type if intent else "generate",
            scope=intent.scope if intent else "full",
            affected_sections=", ".join(intent.affected_sections) if intent and intent.affected_sections else "all",
            incorporate_paper=str(intent.incorporate_paper) if intent else "false",
            repo_analysis=ctx.repo_analysis or "" if ctx else "",
            readme_analysis=ctx.readme_analysis or "" if ctx else "",
            article_analysis=ctx.article_analysis or "N/A" if ctx else "N/A",
            user_request=state.user_request or "Generate a comprehensive README",
            existing_sections=existing_sections,
        ),
        parser=SectionPlanLLMOutput,
    )
    return raw.sections


_FALLBACK_SECTIONS: list[_PlannedSection] = [
    _PlannedSection(
        name="overview",
        title="Overview",
        description="High-level project description",
        prompt_context_keys=["repo_analysis", "readme_analysis"],
    ),
    _PlannedSection(
        name="core_features",
        title="Core Features",
        description="List of main features with brief explanations",
        prompt_context_keys=["repo_analysis", "key_files_content"],
    ),
    _PlannedSection(
        name="getting_started",
        title="Getting Started",
        description="Quick start guide with code examples",
        prompt_context_keys=["repo_analysis", "examples_content", "key_files_content"],
    ),
]


def section_planner_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Produce an ordered list of SectionSpec for the README."""
    logger.info("[SectionPlanner] Planning README sections...")
    logger.debug("[SectionPlanner] Input state summary: %s", summarize_state(state))

    try:
        llm_sections = _build_llm_plan(state, context)
    except (JsonParseError, ValidationError) as exc:
        logger.warning("[SectionPlanner] LLM plan failed (%s); using fallback sections.", exc)
        llm_sections = list(_FALLBACK_SECTIONS)

    if not llm_sections:
        logger.warning("[SectionPlanner] LLM returned empty plan; using fallback sections.")
        llm_sections = list(_FALLBACK_SECTIONS)

    llm_sections = _normalize_llm_sections(llm_sections, state.user_request)

    # Convert LLM output to SectionSpec, assigning priorities starting at 10 (after header)
    plan: list[SectionSpec] = []
    priority = 10
    for sec in llm_sections:
        if sec.name in _DETERMINISTIC_NAMES:
            continue
        plan.append(
            SectionSpec(
                name=sec.name,
                title=sec.title,
                description=sec.description,
                strategy="llm",
                priority=priority,
                prompt_context_keys=sec.prompt_context_keys,
            )
        )
        priority += 10

    # Inject deterministic sections
    for det in DETERMINISTIC_SECTIONS:
        plan.append(det)

    plan.sort(key=lambda s: s.priority)

    logger.info(
        "[SectionPlanner] Planned %d sections: %s",
        len(plan),
        [(s.name, s.strategy) for s in plan],
    )
    update = {"section_plan": plan}
    logger.debug("[SectionPlanner] Output update summary: %s", summarize_update(update))
    return update
