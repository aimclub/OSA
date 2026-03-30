from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.nodes.algorithms import algorithms_node
from osa_tool.operations.docs.readme_generation.agent.nodes.content import content_node
from osa_tool.operations.docs.readme_generation.agent.nodes.core_features import core_features_node
from osa_tool.operations.docs.readme_generation.agent.nodes.getting_started import getting_started_node
from osa_tool.operations.docs.readme_generation.agent.nodes.overview import overview_node
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger


def _extract_generated_section(node_output: dict, section_name: str) -> str | None:
    value = node_output.get(section_name)
    if value is None:
        return None
    if section_name == "core_features":
        return str(value)
    return value if isinstance(value, str) else str(value)


def targeted_executor_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate only resolved target sections for targeted mode."""
    logger.info("[TargetedExecutor] Generating targeted sections...")
    logger.debug("[TargetedExecutor] Input state summary: %s", summarize_state(state))

    sections_to_generate = state.resolved_target_sections or state.target_sections
    generated_sections = dict(state.generated_sections)
    generation_errors = dict(state.section_generation_errors)

    generation_order = sorted(
        sections_to_generate,
        key=lambda name: 0 if name == "core_features" else 1,
    )

    for section_name in generation_order:
        try:
            if section_name == "overview":
                output = overview_node(state, context)
            elif section_name == "core_features":
                output = core_features_node(state, context)
            elif section_name == "getting_started":
                output = getting_started_node(state, context)
            elif section_name == "content":
                output = content_node(state, context)
            elif section_name == "algorithms":
                output = algorithms_node(state, context)
            else:
                logger.warning("[TargetedExecutor] Unknown section '%s', skipping.", section_name)
                continue
        except Exception as exc:
            generation_errors[section_name] = repr(exc)
            logger.warning(
                "[TargetedExecutor] Failed to generate section '%s': %s",
                section_name,
                repr(exc),
            )
            continue

        value = _extract_generated_section(output, section_name)
        if value:
            generated_sections[section_name] = value
            if section_name == "core_features":
                # Keep overview prompt context consistent when both are targeted.
                state.core_features = output.get("core_features")

    logger.info("[TargetedExecutor] Generated sections: %s", list(generated_sections.keys()))
    update = {
        "generated_sections": generated_sections,
        "section_generation_errors": generation_errors,
    }
    logger.debug("[TargetedExecutor] Output update summary: %s", summarize_update(update))
    return update
