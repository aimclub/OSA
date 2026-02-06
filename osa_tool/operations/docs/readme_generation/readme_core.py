import os

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.docs.readme_generation.generator.builder import MarkdownBuilder
from osa_tool.operations.docs.readme_generation.generator.builder_article import MarkdownBuilderArticle
from osa_tool.operations.docs.readme_generation.models.llm_service import LLMClient
from osa_tool.operations.docs.readme_generation.utils import remove_extra_blank_lines, save_sections
from osa_tool.scheduler.todo_list import ToDoList
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class ReadmeAgent:

    def __init__(
        self,
        config_manager: ConfigManager,
        metadata: RepositoryMetadata,
        attachment: str | None = None,
        refine_readme: bool = False,
        todo_list: ToDoList | None = None,
    ):
        self.config_manager = config_manager
        self.article = attachment
        self.refine_readme = refine_readme
        self.metadata = metadata
        self.repo_url = self.config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.file_to_save = os.path.join(self.repo_path, "README.md")
        self.llm_client = LLMClient(self.config_manager, self.metadata)
        self.todo_list = todo_list

    def generate_readme(self) -> dict:
        """
        Generate README.md file.

        Returns:
            dict: Standardized operation output containing:
                - result: Information about generated README
                - events: List of OperationEvent
        """
        logger.info("Started generating README.md. Processing the repository: %s", self.repo_url)
        events: list[OperationEvent] = []

        try:
            if self.article is None:
                builder = self.default_readme()
            else:
                builder = self.article_readme()

            readme_content = builder.build()

            events.append(OperationEvent(kind=EventKind.GENERATED, target="README.md"))

            if self.refine_readme:
                readme_content = self.llm_client.refine_readme(readme_content)
                events.append(OperationEvent(kind=EventKind.REFINED, target="README.md"))
                if self.todo_list is not None:
                    self.todo_list.mark_did("refine_readme")

            if self.article is None:
                readme_content = self.llm_client.clean(readme_content)

            save_sections(readme_content, self.file_to_save)
            remove_extra_blank_lines(self.file_to_save)
            logger.info(f"README.md successfully generated in folder {self.repo_path}")

            return {
                "result": {
                    "file": "README.md",
                    "path": self.file_to_save,
                    "refined": self.refine_readme,
                },
                "events": events,
            }
        except Exception as e:
            logger.error("Error while generating: %s", repr(e), exc_info=True)

            events.append(
                OperationEvent(
                    kind=EventKind.FAILED,
                    target="README.md",
                    data={
                        "reason": "generation_error",
                        "error": repr(e),
                    },
                )
            )

            return {
                "result": None,
                "events": events,
            }

    def default_readme(self) -> MarkdownBuilder:
        responses = self.llm_client.get_responses()
        core_features, overview, getting_started = responses
        return MarkdownBuilder(self.config_manager, self.metadata, overview, core_features, getting_started)

    def article_readme(self) -> MarkdownBuilderArticle:
        responses = self.llm_client.get_responses_article(self.article)
        overview, content, algorithms, getting_started = responses
        return MarkdownBuilderArticle(
            self.config_manager, self.metadata, overview, content, algorithms, getting_started
        )
