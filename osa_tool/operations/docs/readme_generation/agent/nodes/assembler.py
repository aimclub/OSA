"""Assemble generated sections into a coherent README draft."""

from __future__ import annotations

import re

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.utils import build_system_message
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


def _strip_leading_markdown_heading(content: str, title: str) -> str:
    """Remove a redundant top-level heading if templates or the LLM already included it."""
    text = content.strip()
    if not text:
        return text
    m = re.match(rf"^#{{1,3}}\s*{re.escape(title.strip())}\s*\n+", text, re.IGNORECASE)
    if m:
        return text[m.end() :].lstrip()
    return content.strip()


def _toc_anchor_slug(title: str) -> str:
    """Approximate GitHub-style heading anchors for local ToC links."""
    t = title.lower().strip()
    t = re.sub(r"[^\w\s-]", "", t, flags=re.UNICODE)
    t = re.sub(r"\s+", "-", t)
    return t.strip("-")


def _strip_trailing_hr(text: str) -> str:
    """Remove a trailing horizontal rule so we can add a single consistent divider."""
    return re.sub(r"\n+---\s*$", "", text.rstrip())


def _with_trailing_hr(block: str) -> str:
    """End a section block with a horizontal rule (README style between sections)."""
    return f"{_strip_trailing_hr(block)}\n\n---"


def _build_table_of_contents(titles: list[str]) -> str:
    """Generate a markdown ToC from an ordered list of section titles."""
    toc_lines = ["## Table of Contents\n"]
    for title in titles:
        anchor = _toc_anchor_slug(title)
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

        if spec.name == "header":
            if result and result.content.strip():
                parts.append(result.content.rstrip())
            continue

        if spec.name == "table_of_contents":
            toc_insert_index = len(parts)
            parts.append("")  # placeholder; content is synthesized from toc_titles
            continue

        if result is None or not result.content.strip():
            continue

        body = _strip_leading_markdown_heading(result.content, result.title)
        heading = f"## {result.title}"
        block = _with_trailing_hr(f"{heading}\n\n{body}")
        parts.append(block)
        toc_titles.append(result.title)

    if toc_insert_index is not None and toc_titles:
        parts[toc_insert_index] = _with_trailing_hr(_build_table_of_contents(toc_titles).rstrip("\n"))

    return "\n\n".join(part for part in parts if part)


def _assemble_partial(state: ReadmeState, ctx: ReadmeContext) -> str:
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

    existing = state.context.existing_readme if state.context else ""
    try:
        merged = ctx.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                ctx.prompts.get("readme.prompts.section_merge"),
                existing_readme=existing,
                new_sections="\n\n".join(new_parts),
                target_sections=", ".join(target_names),
                generation_plan=state.intent.reasoning if state.intent else "",
            ),
            parser=LlmTextOutput,
            system_message=build_system_message(ctx, "section_merge"),
        ).text
    except Exception as exc:
        logger.warning("[Assembler] section_merge LLM failed; keeping existing README. (%s)", exc)
        return existing

    return merged or existing


def assembler_node(state: ReadmeState, ctx: ReadmeContext) -> dict:
    """Assemble the final README draft from generated sections."""
    logger.info("[Assembler] Assembling README draft...")

    if state.readme_assembly_mode() == "merge_existing":
        readme_draft = _assemble_partial(state, ctx)
    else:
        readme_draft = _assemble_full(state)

    logger.info("[Assembler] Draft assembled (%d chars).", len(readme_draft))
    logger.debug("[Assembler] State after node: %s", state)
    return {
        "readme_draft": readme_draft,
        "sections_to_rerun": [],
        "section_regeneration_hints": {},
    }
