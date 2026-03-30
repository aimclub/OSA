"""Plan which README sections to generate: LLM picks catalog names; metadata comes from section_catalog."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.section_catalog import (
    DEFAULT_FALLBACK_LLM_SECTION_NAMES,
    deterministic_specs_for_plan,
    format_llm_catalog_for_planner,
    section_specs_from_llm_names,
)
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError


class SectionPlanLLMOutput(BaseModel):
    """LLM returns only internal section names; catalog supplies priority, prompts, and context keys."""

    model_config = ConfigDict(extra="ignore")
    section_names: list[str] = Field(default_factory=list)


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


def _normalize_llm_section_names(names: list[str], user_request: str | None) -> list[str]:
    """Drop discouraged sections, resolve overlap, cap count. Order preserved."""
    name_set = {n.strip() for n in names if n and n.strip()}
    out: list[str] = []

    for raw in names:
        n = (raw or "").strip()
        if not n:
            continue
        if n in _DISCOURAGED_BY_DEFAULT and not _user_wants_discouraged(user_request, n):
            continue
        if n == "usage" and "getting_started" in name_set:
            continue
        if n == "notebook_usage" and "getting_started" in name_set:
            continue
        if n == "data_requirements" and "getting_started" in name_set:
            continue
        if n not in out:
            out.append(n)

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


def _build_llm_plan(state: ReadmeState, context: ReadmeContext) -> list[str]:
    """Ask the LLM to propose which LLM catalog sections to include (names only)."""
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
            llm_section_catalog=format_llm_catalog_for_planner(),
        ),
        parser=SectionPlanLLMOutput,
    )
    return [x.strip() for x in raw.section_names if x and x.strip()]


def section_planner_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Produce an ordered list of SectionSpec for the README."""
    logger.info("[SectionPlanner] Planning README sections...")
    logger.debug("[SectionPlanner] Input state summary: %s", summarize_state(state))

    try:
        llm_names = _build_llm_plan(state, context)
    except (JsonParseError, ValidationError) as exc:
        logger.warning("[SectionPlanner] LLM plan failed (%s); using fallback sections.", exc)
        llm_names = list(DEFAULT_FALLBACK_LLM_SECTION_NAMES)

    if not llm_names:
        logger.warning("[SectionPlanner] LLM returned empty plan; using fallback sections.")
        llm_names = list(DEFAULT_FALLBACK_LLM_SECTION_NAMES)

    llm_names = _normalize_llm_section_names(llm_names, state.user_request)

    plan = section_specs_from_llm_names(llm_names, state.intent, state.context)
    plan.extend(deterministic_specs_for_plan(state.intent, state.context))
    plan.sort(key=lambda s: s.priority)

    logger.info(
        "[SectionPlanner] Planned %d sections: %s",
        len(plan),
        [(s.name, s.strategy) for s in plan],
    )
    update = {"section_plan": plan}
    logger.debug("[SectionPlanner] Output update summary: %s", summarize_update(update))
    return update
