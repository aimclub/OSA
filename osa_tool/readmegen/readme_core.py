import os

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.generator.builder import MarkdownBuilder
from osa_tool.readmegen.generator.builder_article import MarkdownBuilderArticle
from osa_tool.readmegen.models.llm_service import LLMClient
from osa_tool.readmegen.utils import remove_extra_blank_lines, save_sections
from osa_tool.scheduler.todo_list import ToDoList
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptLoader
from osa_tool.utils.utils import parse_folder_name


class ReadmeAgent:
    def __init__(
        self,
        config_loader: ConfigLoader,
        prompts: PromptLoader,
        article: str | None,
        refine_readme: bool,
        metadata: RepositoryMetadata,
        todo_list: ToDoList | None = None
    ):
        self.config_loader = config_loader
        self.prompts = prompts
        self.article = article
        self.refine_readme = refine_readme
        self.metadata = metadata
        self.repo_url = self.config_loader.config.git.repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.file_to_save = os.path.join(self.repo_path, "README.md")
        self.llm_client = LLMClient(self.config_loader, self.prompts, self.metadata)
        self.todo_list = todo_list

    def generate_readme(self):
        logger.info("Started generating README.md. Processing the repository: %s", self.repo_url)
        try:
            if self.article is None:
                builder = self.default_readme()
            else:
                builder = self.article_readme()

            readme_content = builder.build()

            if self.refine_readme:
                readme_content = self.llm_client.refine_readme(readme_content)
                if self.todo_list is not None:
                    self.todo_list.mark_did("refine_readme")

            if self.article is None:
                readme_content = self.llm_client.clean(readme_content)

            save_sections(readme_content, self.file_to_save)
            remove_extra_blank_lines(self.file_to_save)
            logger.info(f"README.md successfully generated in folder {self.repo_path}")
        except Exception as e:
            logger.error("Error while generating: %s", repr(e), exc_info=True)
            raise ValueError("Failed to generate README.md.")

    def default_readme(self) -> MarkdownBuilder:
        responses = self.llm_client.get_responses()
        (core_features, overview, getting_started) = responses
        return MarkdownBuilder(
            self.config_loader, self.prompts, self.metadata, overview, core_features, getting_started
        )

    def article_readme(self) -> MarkdownBuilderArticle:
        responses = self.llm_client.get_responses_article(self.article)
        (overview, content, algorithms, getting_started) = responses
        return MarkdownBuilderArticle(
            self.config_loader, self.prompts, self.metadata, overview, content, algorithms, getting_started
        )
