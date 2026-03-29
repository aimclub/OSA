from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.core.models.llm_output_models import LlmTextOutput


def getting_started_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Generate getting started section (both modes)."""
    logger.info("[GettingStarted] Generating getting started section...")

    getting_started = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme.getting_started"),
            project_name=context.metadata.name,
            readme_content=state.existing_readme,
            examples_files_content=state.examples_content,
        ),
        parser=LlmTextOutput,
    ).text

    logger.info("[GettingStarted] Done.")
    return {"getting_started": getting_started}
