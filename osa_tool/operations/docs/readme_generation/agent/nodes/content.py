from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.core.models.llm_output_models import LlmTextOutput


def content_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate content section (article mode)."""
    logger.info("[Content] Generating content section...")
    logger.debug("[Content] Input state summary: %s", summarize_state(state))

    content = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_article.content"),
            project_name=context.metadata.name,
            pdf_summary=state.pdf_summary or "",
            files_summary=state.file_summary or "",
            readme_content=state.existing_readme,
        ),
        parser=LlmTextOutput,
    ).text

    update = {"content": content}
    logger.debug("[Content] Output update summary: %s", summarize_update(update))
    logger.info("[Content] Done.")
    return update
