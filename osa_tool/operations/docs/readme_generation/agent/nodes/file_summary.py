from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor


def file_summary_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate file summary (article mode)."""
    logger.info("[FileSummary] Summarizing key files for article mode...")

    file_summary = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_article.file_summary"),
            files_content=state.key_files_content,
            readme_content=state.existing_readme,
        ),
        parser=lambda raw: JsonProcessor.parse(raw, expected_key="file_summary", expected_type=str),
    )

    logger.info("[FileSummary] Done.")
    return {"file_summary": file_summary}
