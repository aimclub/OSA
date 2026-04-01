"""Public entry point for the README generation operation."""

import os
from typing import Any

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.graph import build_readme_graph
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class ReadmeAgent:
    """Orchestrates a full README generation run via the LangGraph pipeline."""

    def __init__(
        self,
        config_manager: ConfigManager,
        metadata: RepositoryMetadata,
        attachment: str | None = None,
        active_request: str | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.metadata = metadata
        self.attachment = attachment
        self.active_request = active_request

        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.file_to_save = os.path.join(self.repo_path, "README.md")

    def generate_readme(self) -> dict[str, Any]:
        """Run the agent pipeline and return ``{result, events}``."""
        logger.info("========== README GENERATION START ==========")
        logger.info("Processing repository: %s", self.repo_url)

        try:
            context = ReadmeContext(self.config_manager, self.metadata)
            state = ReadmeState(
                repo_url=self.repo_url,
                attachment=self.attachment,
                user_request=self.active_request,
            )

            graph = build_readme_graph(context)
            final = graph.invoke(state)

            events = final.get("events", []) if isinstance(final, dict) else final.events

            logger.info("README.md generated in %s", self.repo_path)
            logger.info("=========== README GENERATION END ===========")
            return {
                "result": {"file": "README.md", "path": self.file_to_save},
                "events": events,
            }
        except Exception as exc:
            logger.error("README generation failed: %s", exc, exc_info=True)
            logger.info("=========== README GENERATION END ===========")
            return {
                "result": None,
                "events": [
                    OperationEvent(
                        kind=EventKind.FAILED,
                        target="README.md",
                        data={"reason": "generation_error", "error": repr(exc)},
                    )
                ],
            }
