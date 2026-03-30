"""Apply whole-README LLM patch using self-eval issues (global refinement path)."""

from __future__ import annotations

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


def readme_patch_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Improve readme_draft in one pass from structured issues."""
    logger.info("[ReadmePatch] Patching README from %d issues...", len(state.refinement_issues))
    logger.debug("[ReadmePatch] Input state summary: %s", summarize_state(state))

    if not state.refinement_issues:
        logger.info("[ReadmePatch] No issues to apply; skipping.")
        return {}

    current = state.readme_draft or ""
    refined = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_agent.refine_with_feedback"),
            readme=current,
            issues="\n".join(f"- {issue}" for issue in state.refinement_issues),
            generation_plan=state.intent.reasoning if state.intent else "",
            user_request=state.user_request or "N/A",
        ),
        parser=LlmTextOutput,
    ).text

    update = {"readme_draft": refined or current}
    logger.debug("[ReadmePatch] Output update summary: %s", summarize_update(update))
    return update
