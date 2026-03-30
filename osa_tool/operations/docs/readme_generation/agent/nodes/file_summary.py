from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.core.models.llm_output_models import LlmTextOutput


def file_summary_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate file summary (article mode)."""
    logger.info("[FileSummary] Summarizing key files for article mode...")
    logger.debug("[FileSummary] Input state summary: %s", summarize_state(state))

    file_summary = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_article.file_summary"),
            files_content=state.key_files_content,
            readme_content=state.existing_readme,
        ),
        parser=LlmTextOutput,
    ).text

    update = {"file_summary": file_summary}
    logger.debug("[FileSummary] Output update summary: %s", summarize_update(update))
    logger.info("[FileSummary] Done.")
    return update
