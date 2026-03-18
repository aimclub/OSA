from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor


def overview_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate overview section (both modes)."""
    logger.info("[Overview] Generating project overview...")

    if state.readme_mode == "article":
        overview = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme_article.overview"),
                project_name=context.metadata.name,
                pdf_summary=state.pdf_summary or "",
                readme_content=state.existing_readme,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="overview", expected_type=str),
        )
    else:
        overview = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme.overview"),
                project_name=context.metadata.name,
                description=context.metadata.description,
                readme_content=state.existing_readme,
                core_features=state.core_features,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="overview", expected_type=str),
        )

    logger.info("[Overview] Done.")
    return {"overview": overview}
