from pydantic import ValidationError

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.llm_schemas import ReadmeSelfEvalLLMOutput
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError


def refiner_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Refine readme_draft with self-evaluation loop.

    Each invocation = one cycle:
      1. If there are issues from a previous cycle, refine the draft to fix them.
      2. Self-evaluate the current draft → score + issues.
      3. Return partial state update so the graph router decides whether to loop or exit.
    """
    cycle = state.refinement_cycles + 1
    logger.info("[Refiner] Refinement cycle %d...", cycle)

    current = state.readme_draft or ""

    # Step 1: Improve the draft
    if state.refinement_issues:
        # Subsequent cycles: targeted fixes based on eval issues
        logger.info("[Refiner] Fixing %d issues from previous evaluation...", len(state.refinement_issues))
        refined = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme_agent.refine_with_feedback"),
                readme=current,
                issues="\n".join(f"- {issue}" for issue in state.refinement_issues),
                generation_plan=state.generation_plan or "",
                user_request=state.user_request or "N/A",
            ),
            parser=LlmTextOutput,
        ).text
        current = refined or current
    elif cycle == 1:
        # First cycle: classic 3-step merge + polish
        current = (
            context.model_handler.send_and_parse(
                prompt=PromptBuilder.render(
                    context.prompts.get("readme.refine_step1"),
                    old_readme=state.existing_readme,
                    new_readme=current,
                ),
                parser=LlmTextOutput,
            ).text
        ) or current
        current = (
            context.model_handler.send_and_parse(
                prompt=PromptBuilder.render(
                    context.prompts.get("readme.refine_step2"),
                    readme=current,
                ),
                parser=LlmTextOutput,
            ).text
        ) or current
        current = (
            context.model_handler.send_and_parse(
                prompt=PromptBuilder.render(
                    context.prompts.get("readme.refine_step3"),
                    readme=current,
                ),
                parser=LlmTextOutput,
            ).text
        ) or current

    # Step 2: Self-evaluate
    try:
        eval_result = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme_agent.self_eval"),
                readme=current,
                repo_analysis=state.repo_analysis or "",
                generation_plan=state.generation_plan or "",
                user_request=state.user_request or "N/A",
                previous_issues=(
                    "\n".join(f"- {i}" for i in state.refinement_issues) if state.refinement_issues else "None"
                ),
            ),
            parser=ReadmeSelfEvalLLMOutput,
        )
        refinement_score = float(eval_result.score)
        refinement_issues = list(eval_result.issues)
        should_stop = eval_result.should_stop
        if should_stop:
            refinement_score = max(refinement_score, 8.0)
        logger.info(
            "[Refiner] Cycle %d: score=%.1f, issues=%d, should_stop=%s",
            cycle,
            refinement_score,
            len(refinement_issues),
            should_stop,
        )
    except (JsonParseError, ValidationError) as e:
        refinement_score = 7.0
        refinement_issues = []
        logger.warning("[Refiner] Self-eval failed after retries (%s); score=7.0", e)

    return {
        "readme_draft": current,
        "refinement_cycles": cycle,
        "refinement_score": refinement_score,
        "refinement_issues": refinement_issues,
    }
