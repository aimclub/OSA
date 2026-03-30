from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger


SECTION_ALIASES: dict[str, str] = {
    "overview": "overview",
    "intro": "overview",
    "introduction": "overview",
    "core_features": "core_features",
    "features": "core_features",
    "getting_started": "getting_started",
    "setup": "getting_started",
    "installation": "getting_started",
    "content": "content",
    "algorithms": "algorithms",
}


def _default_targets_for_mode(readme_mode: str) -> list[str]:
    if readme_mode == "article":
        return ["overview", "content", "algorithms", "getting_started"]
    return ["overview", "core_features", "getting_started"]


def targeted_planner_node(state: ReadmeState, _context: ReadmeContext) -> dict:
    """Resolve target sections for targeted mode."""
    logger.info("[TargetedPlanner] Resolving target sections...")

    requested = state.target_sections or []
    normalized: list[str] = []
    for section in requested:
        key = section.strip().lower()
        if not key:
            continue
        canonical = SECTION_ALIASES.get(key)
        if canonical and canonical not in normalized:
            normalized.append(canonical)

    if not normalized:
        normalized = _default_targets_for_mode(state.readme_mode)
        logger.info(
            "[TargetedPlanner] No valid explicit targets, using defaults for %s: %s",
            state.readme_mode,
            normalized,
        )

    logger.info("[TargetedPlanner] Resolved targets: %s", normalized)
    return {"resolved_target_sections": normalized}
