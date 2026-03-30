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
    return {
        "mode": {
            "generation_mode": state.generation_mode,
            "readme_mode": state.readme_mode,
            "refinement_cycles": state.refinement_cycles,
            "refinement_score": state.refinement_score,
        },
        "targets": {
            "target_sections": state.target_sections,
            "resolved_target_sections": state.resolved_target_sections,
        },
        "content_presence": {
            "repo_tree": _summary_value(state.repo_tree),
            "existing_readme": _summary_value(state.existing_readme),
            "repo_analysis": _summary_value(state.repo_analysis),
            "readme_analysis": _summary_value(state.readme_analysis),
            "article_analysis": _summary_value(state.article_analysis),
            "overview": _summary_value(state.overview),
            "core_features": _summary_value(state.core_features),
            "getting_started": _summary_value(state.getting_started),
            "file_summary": _summary_value(state.file_summary),
            "pdf_summary": _summary_value(state.pdf_summary),
            "content": _summary_value(state.content),
            "algorithms": _summary_value(state.algorithms),
            "generated_sections": _summary_value(state.generated_sections),
            "section_generation_errors": _summary_value(state.section_generation_errors),
            "readme_draft": _summary_value(state.readme_draft),
            "readme_final": _summary_value(state.readme_final),
            "refinement_issues": _summary_value(state.refinement_issues),
        },
    }


def summarize_update(update: dict[str, Any]) -> dict[str, Any]:
    """Compact node output snapshot safe for debug logs."""
    return {key: _summary_value(value) for key, value in update.items()}
