from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


def overview_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate overview section (both modes)."""
    logger.info("[Overview] Generating project overview...")
    logger.debug("[Overview] Input state summary: %s", summarize_state(state))

    if state.readme_mode == "article":
        overview = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme_article.overview"),
                project_name=context.metadata.name,
                pdf_summary=state.pdf_summary or "",
                readme_content=state.existing_readme,
            ),
            parser=LlmTextOutput,
        ).text
    else:
        overview = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme.overview"),
                project_name=context.metadata.name,
                description=context.metadata.description,
                readme_content=state.existing_readme,
                core_features=state.core_features,
            ),
            parser=LlmTextOutput,
        ).text

    update = {"overview": overview}
    logger.debug("[Overview] Output update summary: %s", summarize_update(update))
    logger.info("[Overview] Done.")
    return update
