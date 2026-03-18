from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor


def content_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate content section (article mode)."""
    logger.info("[Content] Generating content section...")

    content = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_article.content"),
            project_name=context.metadata.name,
            pdf_summary=state.pdf_summary or "",
            files_summary=state.file_summary or "",
            readme_content=state.existing_readme,
        ),
        parser=lambda raw: JsonProcessor.parse(raw, expected_key="content", expected_type=str),
    )

    logger.info("[Content] Done.")
    return {"content": content}
