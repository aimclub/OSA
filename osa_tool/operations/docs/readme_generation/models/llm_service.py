import os

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.utils.utils import parse_folder_name, extract_readme_content


class LLMClient:
    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("readme")
        self.metadata = metadata
        self.prompts = self.config_manager.get_prompts()
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)

        self.repo_url = self.config_manager.get_git_settings().repository
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.readme_content = extract_readme_content(self.base_path)

    def get_citation_from_readme(self) -> str:
        logger.info("Detecting citations in README...")
        text = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.citation"),
                readme=self.readme_content,
            ),
            parser=LlmTextOutput,
        ).text
        return text if text is not None else ""

    def get_article_name(self, pdf_content: str) -> str:
        logger.info("Getting article name from pdf...")
        text = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme_article.article_name_extraction"),
                pdf_content=pdf_content,
            ),
            parser=LlmTextOutput,
        ).text
        return text if text is not None else ""
