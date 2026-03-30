"""Generic LLM-powered section generator — produces any README section from a SectionSpec."""

from __future__ import annotations

import re

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_update
from osa_tool.operations.docs.readme_generation.agent.models import SectionResult, SectionSpec
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


def _build_context_block(state: ReadmeState, spec: SectionSpec) -> str:
    """Assemble the context block from the keys requested by the section spec."""
    ctx = state.context
    if ctx is None:
        return ""

    field_map: dict[str, str] = {
        "repo_tree": ctx.repo_tree,
        "existing_readme": ctx.existing_readme,
        "key_files_content": ctx.key_files_content,
        "examples_content": ctx.examples_content,
        "pdf_content": ctx.pdf_content or "",
        "repo_analysis": ctx.repo_analysis or "",
        "readme_analysis": ctx.readme_analysis or "",
        "article_analysis": ctx.article_analysis or "",
    }

    keys = spec.prompt_context_keys or ["repo_analysis"]
    parts: list[str] = []
    for key in keys:
        value = field_map.get(key, "")
        if value:
            label = key.replace("_", " ").upper()
            parts.append(f"### {label}\n{value}")
    return "\n\n".join(parts) if parts else field_map.get("repo_analysis", "")


def _extract_existing_section(readme: str, title: str) -> str:
    """Try to extract the content under a matching heading in the existing README."""
    if not readme:
        return ""
    pattern = rf"^##\s+{re.escape(title)}\s*\n(.*?)(?=^##\s|\Z)"
    match = re.search(pattern, readme, re.MULTILINE | re.DOTALL)
    return match.group(1).strip() if match else ""


def section_generator_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate a single README section described by ``state.current_section``."""
    spec: SectionSpec | None = state.current_section
    if spec is None:
        logger.error("[SectionGenerator] No current_section set — skipping.")
        return {}

    logger.info("[SectionGenerator] Generating section '%s' (%s)...", spec.name, spec.title)

    context_block = _build_context_block(state, spec)

    existing_section = ""
    if state.intent and state.intent.task_type in ("improve", "update"):
        existing_section = _extract_existing_section(state.context.existing_readme if state.context else "", spec.title)

    text = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_agent.section_generate"),
            section_title=spec.title,
            section_description=spec.description or spec.title,
            project_name=context.metadata.name,
            context_block=context_block,
            existing_section=existing_section or "N/A",
            user_request=state.user_request or "N/A",
        ),
        parser=LlmTextOutput,
    ).text

    result = SectionResult(
        name=spec.name,
        title=spec.title,
        content=text or "",
        source="llm",
    )

    merged = dict(state.sections)
    merged[spec.name] = result

    update = {"sections": merged}
    logger.debug("[SectionGenerator] Output update summary: %s", summarize_update(update))
    logger.info("[SectionGenerator] Section '%s' done (%d chars).", spec.name, len(result.content))
    return update
