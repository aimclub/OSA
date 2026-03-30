"""Self-evaluation refinement loop — scores the draft and fixes identified issues."""

from pydantic import ValidationError

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.llm_schemas import ReadmeSelfEvalLLMOutput
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError


def refiner_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Single refinement cycle: fix issues (if any) then self-evaluate.

    The graph router decides whether to loop back or proceed to writer.
    """
    cycle = state.refinement_cycles + 1
    logger.info("[Refiner] Refinement cycle %d...", cycle)
    logger.debug("[Refiner] Input state summary: %s", summarize_state(state))

    current = state.readme_draft or ""

    # ── Step 1: Apply targeted fixes if previous cycle found issues ──
    if state.refinement_issues:
        logger.info("[Refiner] Fixing %d issues from previous evaluation...", len(state.refinement_issues))
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
        current = refined or current

    # ── Step 2: Self-evaluate ──
    try:
        eval_result = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme_agent.self_eval"),
                readme=current,
                repo_analysis=state.context.repo_analysis or "" if state.context else "",
                generation_plan=state.intent.reasoning if state.intent else "",
                user_request=state.user_request or "N/A",
                previous_issues=(
                    "\n".join(f"- {i}" for i in state.refinement_issues) if state.refinement_issues else "None"
                ),
            ),
            parser=ReadmeSelfEvalLLMOutput,
        )
        refinement_score = float(eval_result.score)
        refinement_issues = list(eval_result.issues)
        if eval_result.should_stop:
            refinement_score = max(refinement_score, 8.0)
        logger.info(
            "[Refiner] Cycle %d: score=%.1f, issues=%d, should_stop=%s",
            cycle,
            refinement_score,
            len(refinement_issues),
            eval_result.should_stop,
        )
    except (JsonParseError, ValidationError) as exc:
        refinement_score = 7.0
        refinement_issues = []
        logger.warning("[Refiner] Self-eval failed (%s); defaulting score=7.0", exc)

    update = {
        "readme_draft": current,
        "refinement_cycles": cycle,
        "refinement_score": refinement_score,
        "refinement_issues": refinement_issues,
    }
    logger.debug("[Refiner] Output update summary: %s", summarize_update(update))
    return update
