"""Assemble generated sections into a coherent README draft."""

from __future__ import annotations

import re

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder

_SKIP_HEADING = frozenset({"header", "table_of_contents"})


def _build_table_of_contents(titles: list[str]) -> str:
    """Generate a markdown ToC from an ordered list of section titles."""
    toc_lines = ["## Table of Contents\n"]
    for title in titles:
        anchor = re.sub(r"\s+", "-", title.lower())
        toc_lines.append(f"- [{title}](#{anchor})")
    toc_lines.append("\n---")
    return "\n".join(toc_lines)


def _assemble_full(state: ReadmeState) -> str:
    """Concatenate all sections in plan-priority order with headings."""
    plan_order = sorted(state.section_plan, key=lambda s: s.priority)

    parts: list[str] = []
    toc_titles: list[str] = []
    toc_insert_index: int | None = None

    for spec in plan_order:
        result = state.sections.get(spec.name)
        if result is None or not result.content:
            continue

        if spec.name == "header":
            parts.append(result.content)
            continue

        if spec.name == "table_of_contents":
            toc_insert_index = len(parts)
            parts.append("")  # placeholder
            continue

        heading = f"## {result.title}"
        parts.append(f"{heading}\n\n{result.content}")
        toc_titles.append(result.title)

    if toc_insert_index is not None and toc_titles:
        parts[toc_insert_index] = _build_table_of_contents(toc_titles)

    return "\n\n".join(part for part in parts if part)


def _assemble_partial(state: ReadmeState, context: ReadmeContext) -> str:
    """Merge newly generated sections into the existing README via LLM."""
    new_parts: list[str] = []
    target_names: list[str] = []

    for spec in sorted(state.section_plan, key=lambda s: s.priority):
        if spec.strategy == "keep_existing":
            continue
        result = state.sections.get(spec.name)
        if result and result.content:
            new_parts.append(f"### {result.title}\n{result.content}")
            target_names.append(result.title)

    if not new_parts:
        return state.context.existing_readme if state.context else ""

    merged = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_agent.section_merge"),
            existing_readme=state.context.existing_readme if state.context else "",
            new_sections="\n\n".join(new_parts),
            target_sections=", ".join(target_names),
            generation_plan=state.intent.reasoning if state.intent else "",
        ),
        parser=LlmTextOutput,
    ).text

    return merged or (state.context.existing_readme if state.context else "")


def assembler_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Assemble the final README draft from generated sections."""
    logger.info("[Assembler] Assembling README draft...")
    logger.debug("[Assembler] Input state summary: %s", summarize_state(state))

    is_partial = state.intent and state.intent.scope == "partial" and state.intent.task_type == "update"

    if is_partial:
        readme_draft = _assemble_partial(state, context)
    else:
        readme_draft = _assemble_full(state)

    update = {"readme_draft": readme_draft}
    logger.debug("[Assembler] Output update summary: %s", summarize_update(update))
    logger.info("[Assembler] Draft assembled (%d chars).", len(readme_draft))
    return update
