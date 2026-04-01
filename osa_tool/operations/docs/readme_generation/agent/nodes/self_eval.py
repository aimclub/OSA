"""Self-evaluate the assembled README draft (score + issues + optional section rerun plan)."""

from pydantic import ValidationError

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.models import SectionSpec
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.utils import build_system_message
from osa_tool.operations.docs.readme_generation.llm_schemas import ReadmeSelfEvalLLMOutput
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError


def _filter_sections_to_rerun(names: list[str], section_plan: list[SectionSpec]) -> list[str]:
    """Keep only names that match planned LLM sections (same contract as graph regen sends)."""
    valid = {s.name for s in section_plan if s.strategy == "llm"}
    kept: list[str] = []
    for n in names:
        if n in valid:
            kept.append(n)
        else:
            logger.warning("[SelfEval] Dropping invalid sections_to_rerun (not a planned LLM section): %s", n)
    return kept


def self_eval_node(state: ReadmeState, ctx: ReadmeContext) -> dict:
    """Score the current readme_draft and optionally request LLM section regeneration."""
    cycle = state.refinement_cycles + 1
    logger.info("[SelfEval] Evaluation cycle %d...", cycle)

    planned_names = ", ".join(s.name for s in state.section_plan)
    intent_scope = state.intent.scope if state.intent else "N/A"
    intent_task_type = state.intent.task_type if state.intent else "N/A"
    affected_sections = (
        ", ".join(state.intent.affected_sections) if state.intent and state.intent.affected_sections else "N/A"
    )
    assembly_mode = state.readme_assembly_mode()

    try:
        eval_result = ctx.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                ctx.prompts.get("readme.prompts.self_eval"),
                readme=state.readme_draft or "",
                repo_analysis=state.context.repo_analysis or "" if state.context else "",
                generation_plan=state.intent.reasoning if state.intent else "",
                user_request=state.user_request or "N/A",
                previous_issues=(
                    "\n".join(f"- {i}" for i in state.refinement_issues) if state.refinement_issues else "None"
                ),
                planned_section_names=planned_names,
                intent_scope=intent_scope,
                intent_task_type=intent_task_type,
                affected_sections=affected_sections,
                assembly_mode=assembly_mode,
            ),
            parser=ReadmeSelfEvalLLMOutput,
            system_message=build_system_message(ctx, "self_eval"),
        )
        refinement_score = float(eval_result.score)
        refinement_issues = list(eval_result.issues)
        sections_to_rerun = _filter_sections_to_rerun(
            [x.strip() for x in eval_result.sections_to_rerun if x and str(x).strip()],
            state.section_plan,
        )
        hints_raw = eval_result.section_feedback if eval_result.section_feedback else {}
        section_regeneration_hints = {str(k).strip(): str(v).strip() for k, v in hints_raw.items() if k}
        if eval_result.should_stop:
            refinement_score = max(refinement_score, 8.0)
        logger.info(
            "[SelfEval] Cycle %d: score=%.1f, issues=%d, should_stop=%s, rerun=%s",
            cycle,
            refinement_score,
            len(refinement_issues),
            eval_result.should_stop,
            sections_to_rerun,
        )
    except (JsonParseError, ValidationError) as exc:
        refinement_score = 7.0
        refinement_issues = []
        sections_to_rerun = []
        section_regeneration_hints = {}
        logger.warning("[SelfEval] Parse failed (%s); defaulting score=7.0", exc)

    logger.debug("[SelfEval] State after node: %s", state)
    return {
        "refinement_cycles": cycle,
        "refinement_score": refinement_score,
        "refinement_issues": refinement_issues,
        "sections_to_rerun": sections_to_rerun,
        "section_regeneration_hints": section_regeneration_hints,
    }
