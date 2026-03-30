"""Compact debug-logging helpers for the README generation pipeline."""

from collections.abc import Mapping
from typing import Any

from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState


def _clip(value: str, max_len: int = 120) -> str:
    if len(value) <= max_len:
        return value
    return f"{value[: max_len - 3]}..."


def _summary_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return {"len": len(value), "preview": _clip(value)}
    if isinstance(value, list):
        return {"count": len(value), "sample": value[:5]}
    if isinstance(value, Mapping):
        return {"keys": list(value.keys())[:8], "count": len(value)}
    return str(value)


def summarize_state(state: ReadmeState) -> dict[str, Any]:
    """Compact state snapshot safe for debug logs."""
    ctx = state.context
    intent = state.intent
    return {
        "intent": {
            "task_type": intent.task_type if intent else None,
            "scope": intent.scope if intent else None,
            "affected_sections": intent.affected_sections if intent else [],
            "incorporate_paper": intent.incorporate_paper if intent else False,
        },
        "plan": {
            "section_count": len(state.section_plan),
            "section_names": [s.name for s in state.section_plan],
        },
        "refinement": {
            "cycles": state.refinement_cycles,
            "score": state.refinement_score,
        },
        "content_presence": {
            "context_present": ctx is not None,
            "repo_tree": _summary_value(ctx.repo_tree) if ctx else None,
            "existing_readme": _summary_value(ctx.existing_readme) if ctx else None,
            "repo_analysis": _summary_value(ctx.repo_analysis) if ctx else None,
            "sections_generated": _summary_value(state.sections),
            "section_errors": _summary_value(state.section_errors),
            "readme_draft": _summary_value(state.readme_draft),
            "readme_final": _summary_value(state.readme_final),
        },
    }


def summarize_update(update: dict[str, Any]) -> dict[str, Any]:
    """Compact node output snapshot safe for debug logs."""
    return {key: _summary_value(value) for key, value in update.items()}
