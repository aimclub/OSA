import os

from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.utils import remove_extra_blank_lines, save_sections
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import parse_folder_name


def writer_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Write final README to disk, emit events."""
    logger.info("[Writer] Writing README.md to disk...")

    repo_path = os.path.join(os.getcwd(), parse_folder_name(state.repo_url))
    file_to_save = os.path.join(repo_path, "README.md")

    readme_content = state.readme_draft or ""

    # Clean for standard mode (matches original behavior)
    if state.readme_mode == "standard":
        for step in ("readme.clean_step1", "readme.clean_step2", "readme.clean_step3"):
            cleaned = context.model_handler.send_and_parse(
                prompt=PromptBuilder.render(
                    context.prompts.get(step),
                    readme=readme_content,
                ),
                parser=LlmTextOutput,
            ).text
            readme_content = cleaned or readme_content

    save_sections(readme_content, file_to_save)
    remove_extra_blank_lines(file_to_save)

    events = list(state.events)
    events.append(OperationEvent(kind=EventKind.GENERATED, target="README.md"))
    if state.refinement_cycles > 0:
        events.append(OperationEvent(kind=EventKind.REFINED, target="README.md"))

    logger.info("[Writer] README.md written to %s", file_to_save)
    return {
        "readme_final": readme_content,
        "events": events,
    }
