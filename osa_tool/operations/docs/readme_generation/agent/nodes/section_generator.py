"""Generate or rebuild one README section from a SectionSpec (LLM or deterministic)."""

from __future__ import annotations

import re

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.models import SectionResult, SectionSpec
from osa_tool.operations.docs.readme_generation.agent.nodes.deterministic_builder import (
    build_single_deterministic_section,
)
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.utils import build_system_message
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


def _strip_leading_section_heading(text: str, title: str) -> str:
    """Remove duplicate headings the model may emit despite instructions."""
    s = (text or "").strip()
    if not s:
        return s
    m = re.match(rf"^#{{1,3}}\s*{re.escape(title)}\s*\n+", s, re.IGNORECASE)
    if m:
        return s[m.end() :].lstrip()
    return s


def section_generator_node(state: ReadmeState, ctx: ReadmeContext) -> dict:
    """Generate a single README section described by ``state.current_section``."""
    spec: SectionSpec | None = state.current_section
    if spec is None:
        logger.error("[SectionGenerator] No current_section set — skipping.")
        return {}

    logger.info("[SectionGenerator] Generating section '%s' (%s)...", spec.name, spec.title)

    if spec.strategy == "keep_existing":
        return {}

    if spec.strategy == "deterministic":
        result, err = build_single_deterministic_section(spec, ctx)
        if err:
            return {"section_errors": {spec.name: err}}
        if result is None:
            return {}
        logger.info("[SectionGenerator] Section '%s' done (deterministic, %d chars).", spec.name, len(result.content))
        return {"sections": {spec.name: result}}

    # --- LLM ---
    context_block = _build_context_block(state, spec)

    existing_section = ""
    if state.intent and state.intent.task_type in ("improve", "update"):
        existing_section = _extract_existing_section(state.context.existing_readme if state.context else "", spec.title)

    reg_hint = ""
    if state.section_regeneration_hints:
        reg_hint = (state.section_regeneration_hints.get(spec.name) or "").strip()

    template_key = spec.prompt_template_key or "readme.prompts.section_generate"
    template = ctx.prompts.get(template_key)
    if template is None:
        logger.error("[SectionGenerator] Missing prompt template '%s' and fallback; aborting section.", template_key)
        return {}

    text = ctx.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            template,
            section_name=spec.name,
            section_title=spec.title,
            section_description=spec.description or spec.title,
            project_name=ctx.metadata.name,
            context_block=context_block,
            existing_section=existing_section or "N/A",
            user_request=state.user_request or "N/A",
            regeneration_hint=reg_hint or "N/A",
        ),
        parser=LlmTextOutput,
        system_message=build_system_message(ctx, "section_generate"),
    ).text

    text = _strip_leading_section_heading(text or "", spec.title)

    result = SectionResult(
        name=spec.name,
        title=spec.title,
        content=text,
        source="llm",
    )

    logger.info("[SectionGenerator] Section '%s' done (llm, %d chars).", spec.name, len(result.content))
    return {"sections": {spec.name: result}}
