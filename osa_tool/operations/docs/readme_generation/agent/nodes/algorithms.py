from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.core.models.llm_output_models import LlmTextOutput


def algorithms_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate algorithms section (article mode)."""
    logger.info("[Algorithms] Generating algorithm descriptions...")

    algorithms = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_article.algorithms"),
            project_name=context.metadata.name,
            files_content=state.key_files_content,
            pdf_summary=state.pdf_summary or "",
            readme_content=state.existing_readme,
        ),
        parser=LlmTextOutput,
    ).text

    logger.info("[Algorithms] Done.")
    return {"algorithms": algorithms}
