import os

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.operations.docs.readme_generation.agent import (
    ReadmeContext,
    ReadmeState,
    build_readme_graph,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class ReadmeAgent:

    def __init__(
        self,
        config_manager: ConfigManager,
        metadata: RepositoryMetadata,
        attachment: str | None = None,
        active_request: str | None = None,
    ):
        self.config_manager = config_manager
        self.metadata = metadata
        self.attachment = attachment
        self.active_request = active_request

        self.repo_url = self.config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.file_to_save = os.path.join(self.repo_path, "README.md")

    def generate_readme(self) -> dict:
        """Generate README.md file via the LangGraph agent pipeline.

        Returns:
            dict: Standardized operation output containing:
                - result: Information about generated README
                - events: List of OperationEvent
        """
        logger.info("========== README GENERATION START ==========")
        logger.info("Started generating README.md. Processing the repository: %s", self.repo_url)

        try:
            context = ReadmeContext(self.config_manager, self.metadata)
            state = ReadmeState(
                repo_url=self.repo_url,
                attachment=self.attachment,
                user_request=self.active_request,
            )

            graph = build_readme_graph(context)
            final = graph.invoke(state)

            # LangGraph returns a dict when state is a Pydantic model
            if isinstance(final, dict):
                events = final.get("events", [])
            else:
                events = final.events

            logger.info("README.md successfully generated in folder %s", self.repo_path)
            logger.info("=========== README GENERATION END ===========")
            return {
                "result": {
                    "file": "README.md",
                    "path": self.file_to_save,
                },
                "events": events,
            }
        except Exception as e:
            logger.error("Error while generating: %s", repr(e), exc_info=True)
            logger.info("=========== README GENERATION END ===========")
            return {
                "result": None,
                "events": [
                    OperationEvent(
                        kind=EventKind.FAILED,
                        target="README.md",
                        data={"reason": "generation_error", "error": repr(e)},
                    )
                ],
            }
