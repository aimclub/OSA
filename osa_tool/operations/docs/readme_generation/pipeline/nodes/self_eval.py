"""Self-evaluate the assembled README draft (structured issues + optional section rerun plan)."""

from pydantic import ValidationError

from osa_tool.operations.docs.readme_generation.pipeline.llm_schemas import ReadmeSelfEvalLLMOutput, SelfEvalIssue
from osa_tool.operations.docs.readme_generation.pipeline.models import SectionSpec
from osa_tool.operations.docs.readme_generation.pipeline.runtime_context import ReadmeContext
from osa_tool.operations.docs.readme_generation.pipeline.state import ReadmeState
from osa_tool.operations.docs.readme_generation.readme_utils import build_system_message
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError

_PARSE_FAILURE_ISSUE = SelfEvalIssue(
    severity="major",
    description="Self-evaluation output could not be parsed; review the README draft manually.",
)
_NO_ISSUE_DESCRIPTION = "(no description provided)"


def _derived_refinement_score(issues: list[SelfEvalIssue]) -> float:
    """Log-only heuristic from severity counts (not used for routing)."""
    blockers = sum(1 for i in issues if i.severity == "blocker")
    majors = sum(1 for i in issues if i.severity == "major")
    minors = sum(1 for i in issues if i.severity == "minor")
    return max(0.0, min(10.0, 10.0 - 3.0 * blockers - 2.0 * majors - 0.5 * minors))


def _structured_issues_to_strings(issues: list[SelfEvalIssue]) -> list[str]:
    lines: list[str] = []
    for item in issues:
        desc = (item.description or "").strip()
        if not desc:
            if item.severity in ("blocker", "major"):
                desc = _NO_ISSUE_DESCRIPTION
            else:
                continue
        lines.append(f"({item.severity}) {desc}")
    return lines


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


def _compute_effective_finish(
    should_stop: bool,
    structured: list[SelfEvalIssue],
    sections_to_rerun: list[str],
) -> bool:
    has_blocker_or_major = any(i.severity in ("blocker", "major") for i in structured)
    if should_stop and has_blocker_or_major:
        logger.warning(
            "[SelfEval] Model set should_stop despite blocker/major issues; continuing refinement.",
        )
    if should_stop and sections_to_rerun:
        logger.warning(
            "[SelfEval] Model set should_stop but sections_to_rerun is non-empty; regenerating sections first.",
        )
    return bool(
        should_stop and not has_blocker_or_major and not sections_to_rerun,
    )


def self_eval_node(state: ReadmeState, ctx: ReadmeContext) -> dict:
    """Evaluate readme_draft and optionally request LLM section regeneration or patching."""
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
        structured = list(eval_result.issues)
        refinement_issues = _structured_issues_to_strings(structured)
        sections_to_rerun = _filter_sections_to_rerun(
            [x.strip() for x in eval_result.sections_to_rerun if x and str(x).strip()],
            state.section_plan,
        )
        hints_raw = eval_result.section_feedback if eval_result.section_feedback else {}
        section_regeneration_hints = {str(k).strip(): str(v).strip() for k, v in hints_raw.items() if k}
        refinement_effective_finish = _compute_effective_finish(
            eval_result.should_stop,
            structured,
            sections_to_rerun,
        )
        refinement_score = _derived_refinement_score(structured)
        if eval_result.quality_notes:
            logger.debug("[SelfEval] quality_notes=%s", eval_result.quality_notes)
        logger.info(
            "[SelfEval] Cycle %d: derived_score=%.1f, issues=%d, effective_finish=%s, should_stop=%s, rerun=%s",
            cycle,
            refinement_score,
            len(structured),
            refinement_effective_finish,
            eval_result.should_stop,
            sections_to_rerun,
        )
    except (JsonParseError, ValidationError) as exc:
        structured = [_PARSE_FAILURE_ISSUE]
        refinement_issues = _structured_issues_to_strings(structured)
        sections_to_rerun = []
        section_regeneration_hints = {}
        refinement_effective_finish = False
        refinement_score = _derived_refinement_score(structured)
        logger.warning("[SelfEval] Parse failed (%s); using fallback major issue.", exc)

    logger.debug("[SelfEval] State after node: %s", state)
    return {
        "refinement_cycles": cycle,
        "refinement_score": refinement_score,
        "refinement_structured_issues": [i.model_dump() for i in structured],
        "refinement_effective_finish": refinement_effective_finish,
        "refinement_issues": refinement_issues,
        "sections_to_rerun": sections_to_rerun,
        "section_regeneration_hints": section_regeneration_hints,
    }
