from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor


def pdf_summary_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate PDF summary (article mode)."""
    logger.info("[PdfSummary] Summarizing PDF content...")

    pdf_summary = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_article.pdf_summary"),
            pdf_content=state.pdf_content or "",
        ),
        parser=lambda raw: JsonProcessor.parse(raw, expected_key="pdf_summary", expected_type=str),
    )

    logger.info("[PdfSummary] Done.")
    return {"pdf_summary": pdf_summary}
