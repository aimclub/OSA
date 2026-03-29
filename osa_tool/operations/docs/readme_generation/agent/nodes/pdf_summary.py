from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.core.models.llm_output_models import LlmTextOutput


def pdf_summary_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate PDF summary (article mode)."""
    logger.info("[PdfSummary] Summarizing PDF content...")

    pdf_summary = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_article.pdf_summary"),
            pdf_content=state.pdf_content or "",
        ),
        parser=LlmTextOutput,
    ).text

    logger.info("[PdfSummary] Done.")
    return {"pdf_summary": pdf_summary}
