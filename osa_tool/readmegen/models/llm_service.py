import os

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.readmegen.context.files_contents import FileContext, FileProcessor
from osa_tool.readmegen.postprocessor.response_cleaner import process_text
from osa_tool.readmegen.prompts.prompts_article_config import PromptArticleLoader
from osa_tool.readmegen.prompts.prompts_builder import (
    get_files_summary_prompt,
    get_getting_started_prompt,
    get_pdf_summary_prompt,
    get_prompt_core_features,
    get_prompt_overview,
    get_prompt_preanalysis,
    get_prompt_overview_article,
    get_prompt_content_article,
    get_prompt_algorithms_article
)
from osa_tool.readmegen.prompts.prompts_config import PromptLoader
from osa_tool.readmegen.utils import extract_example_paths, extract_relative_paths
from osa_tool.utils import logger, parse_folder_name


class LLMClient:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.prompts = PromptLoader().prompts
        self.prompts_article = PromptArticleLoader().prompts
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

    def get_responses(self) -> tuple[str, str, str]:
        """
        Retrieves core features and an overview of the project by processing key files
        and sending requests to the model for the necessary information.

        Returns:
            tuple[str, str]: A tuple containing:
                - core_features: A string representing the core features of the project.
                - overview: A string providing a concise overview of the project.
        """
        key_files = self.get_key_files()
        key_files_content = FileProcessor(self.config_loader, key_files).process_files()

        core_features = self.get_core_features(key_files_content)
        overview = self.get_overview(core_features)

        core_features = process_text(core_features)
        overview = process_text(overview)

        getting_started = None
        if self.sourcerank.examples_presence():
            examples_files = extract_example_paths(self.tree)
            if examples_files:
                examples_content = FileProcessor(self.config_loader, examples_files).process_files()
                getting_started = self.get_getting_started(examples_content)
                getting_started = process_text(getting_started)

        return core_features, overview, getting_started

    def get_responses_article(self, article: str) -> tuple[str, str, str]:
        key_files = self.get_key_files()
        key_files_content = FileProcessor(self.config_loader, key_files).process_files()
        files_summary = self.get_files_summary(key_files_content)

        path_to_pdf = get_pdf_path(article)
        pdf_content = PdfParser(path_to_pdf).data_extractor()
        pdf_summary = self.get_pdf_summary(pdf_content)

        overview = self.get_overview_article(files_summary, pdf_summary)
        content = self.get_content_article(key_files_content, pdf_summary)
        algorithms = self.get_algorithms_article(files_summary, pdf_summary)

        overview = process_text(overview)
        content = process_text(content)
        algorithms = process_text(algorithms)

        return overview, content, algorithms


    def get_key_files(self) -> list[str]:
        """
        Identifies and returns the key files that are essential for the project analysis.

        Sends a request to the model using the preanalysis prompt and returns the relative paths
        of the identified key files.

        Returns:
            list[str]: List of relative paths to the key files identified by the model.
        """
        prompt = get_prompt_preanalysis(self.prompts.preanalysis, self.tree, self.base_path)
        response = self.model_handler.send_request(prompt)
        cleaned_response = process_text(response)

        key_files = extract_relative_paths(cleaned_response)
        logger.info("Primary analysis completed successfully. Key files have been identified.")
        return key_files

    def get_core_features(self, key_files_context: list[FileContext]) -> str:
        """
        Retrieves the core features of the project based on the key files' context.

        Sends a request to the model using the core features prompt and returns the core features
        of the project based on the identified key files.

        Args:
            key_files_context: The list of file contexts for the key files.

        Returns:
            str: The core features of the project.
        """
        prompt = get_prompt_core_features(self.prompts.core_features, self.metadata, self.base_path, key_files_context)
        response = self.model_handler.send_request(prompt)
        logger.info("Core features analysis completed successfully.")
        return response

    def get_overview(self, core_features: str) -> str:
        """
        Retrieves an overview of the project based on the core features.

        Sends a request to the model using the overview prompt and returns a comprehensive overview
        of the project.

        Args:
            core_features: The core features of the project.

        Returns:
            str: The overview of the project.
        """
        prompt = get_prompt_overview(self.prompts.overview, self.metadata, self.base_path, core_features)
        response = self.model_handler.send_request(prompt)
        logger.info("Overview analysis completed successfully.")
        return response

    def get_getting_started(self, examples_context: list[FileContext]) -> str:
        prompt = get_getting_started_prompt(self.prompts.getting_started, self.metadata, self.base_path, examples_context)
        response = self.model_handler.send_request(prompt)
        logger.info("Getting Started analysis completed successfully.")
        return response

    def get_files_summary(self, files_content: list[FileContext]) -> str:
        prompt = get_files_summary_prompt(self.prompts_article.file_summary, files_content)
        response = self.model_handler.send_request(prompt)
        logger.info("Files summary analysis completed successfully.")
        return response

    def get_pdf_summary(self, pdf_content: str) -> str:
        prompt = get_pdf_summary_prompt(self.prompts_article.pdf_summary, pdf_content)
        response = self.model_handler.send_request(prompt)
        logger.info("PDF Summary analysis completed successfully.")
        return response

    def get_overview_article(self, files_summary: str, pdf_summary: str) -> str:
        prompt = get_prompt_overview_article(self.prompts_article.overview, self.metadata, files_summary, pdf_summary)
        response = self.model_handler.send_request(prompt)
        logger.info("Overview analysis completed successfully.")
        return response

    def get_content_article(self, key_files_context: list[FileContext], pdf_summary: str) -> str:
        prompt = get_prompt_content_article(self.prompts_article.content, self.metadata, key_files_context, pdf_summary)
        response = self.model_handler.send_request(prompt)
        logger.info("Content analysis completed successfully.")
        return response

    def get_algorithms_article(self, files_summary: str, pdf_summary: str) -> str:
        prompt = get_prompt_algorithms_article(self.prompts_article.overview, self.metadata, files_summary, pdf_summary)
        response = self.model_handler.send_request(prompt)
        logger.info("Algorithms analysis completed successfully.")
        return response


