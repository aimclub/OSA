"""Apply whole-README LLM patch using self-eval issues (global refinement path)."""

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.utils import build_system_message
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


def readme_patch_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Improve readme_draft in one pass from structured issues."""
    logger.info("[ReadmePatch] Patching README from %d issues...", len(state.refinement_issues))

    if not state.refinement_issues:
        logger.info("[ReadmePatch] No issues to apply; skipping.")
        return {}

    current = state.readme_draft or ""
    intent_scope = state.intent.scope if state.intent else "N/A"
    affected_sections = (
        ", ".join(state.intent.affected_sections) if state.intent and state.intent.affected_sections else "N/A"
    )
    assembly_mode = state.readme_assembly_mode()
    try:
        refined = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme.prompts.refine_with_feedback"),
                readme=current,
                issues="\n".join(f"- {issue}" for issue in state.refinement_issues),
                generation_plan=state.intent.reasoning if state.intent else "",
                user_request=state.user_request or "N/A",
                intent_scope=intent_scope,
                affected_sections=affected_sections,
                assembly_mode=assembly_mode,
            ),
            parser=LlmTextOutput,
            system_message=build_system_message(context, "refine_with_feedback"),
        ).text
    except Exception as exc:
        logger.warning("[ReadmePatch] refine_with_feedback failed; draft unchanged. (%s)", exc)
        refined = current

    logger.debug("[ReadmePatch] State after node: %s", state)
    return {"readme_draft": refined or current}
