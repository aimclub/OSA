from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.operations.docs.readme_generation.llm_schemas import CoreFeaturesLLMOutput


def core_features_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate core features section (standard mode)."""
    logger.info("[CoreFeatures] Generating core features...")

    core_features = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme.core_features"),
            project_name=context.metadata.name,
            metadata=context.metadata,
            readme_content=state.existing_readme,
            key_files_content=state.key_files_content,
        ),
        parser=CoreFeaturesLLMOutput,
    ).features

    logger.info("[CoreFeatures] Done.")
    return {"core_features": [item.model_dump() for item in core_features]}
