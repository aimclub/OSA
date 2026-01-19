import asyncio

from osa_tool.config.settings import ConfigManager
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.validation.code_analyzer import CodeAnalyzer


class PaperValidator:
    """
    Validates a scientific paper (PDF) against the code repository.

    This class extracts and processes the content of a paper, analyzes code files in the repository,
    and validates the paper against the codebase using a language model.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the PaperValidator.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
        """
        self.config_manager = config_manager
        self.code_analyzer = CodeAnalyzer(config_manager)
        self.model_settings = config_manager.get_model_settings('validation')
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.prompts = self.config_manager.get_prompts()

    async def validate(self, article: str | None) -> dict | None:
        """
        Asynchronously validate a scientific paper against the code repository.

        Args:
            article (str | None): Path to the paper PDF file.

        Returns:
            dict | None: Validation result from the language model or none if an error occurs.

        Raises:
            ValueError: If the article path is missing.
            Exception: If an error occurs during validation.
        """
        if not article:
            raise ValueError("Article is missing! Please pass it using --attachment argument.")
        try:
            paper_info = await self.process_paper(article)
            code_files = await asyncio.to_thread(self.code_analyzer.get_code_files)
            code_files_info = await self.code_analyzer.process_code_files(code_files)
            result = await self.validate_paper_against_repo(paper_info, code_files_info)
            return result
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")
            return None

    async def process_paper(self, article: str) -> str:
        """
        Asynchronously extract and process content from a scientific paper (PDF).

        Args:
            article (str): Path to the paper PDF file.

        Returns:
            str: Processed paper content.

        Raises:
            ValueError: If the PDF source is invalid.
        """
        logger.info("Loading PDF...")
        path_to_pdf = get_pdf_path(article)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Extracting text from PDF ...")
        pdf_content = await asyncio.to_thread(PdfParser(path_to_pdf).data_extractor)
        logger.info("Sending request to extract sections ...")
        response = await self.model_handler.async_send_and_parse(
            PromptBuilder.render(
                self.prompts.get("validation.extract_paper_section"),
                paper_content=pdf_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.debug(response)
        return response

    async def validate_paper_against_repo(self, paper_info: str, code_files_info: str) -> dict:
        """
        Asynchronously validate the processed paper content against the code repository.

        Args:
            paper_info (str): Processed paper information.
            code_files_info (str): Aggregated code files analysis.

        Returns:
            dict: Validation result from the language model.
        """
        logger.info("Validating paper against repository ...")
        response = await self.model_handler.async_send_and_parse(
            PromptBuilder.render(
                self.prompts.get("validation.validate_paper_against_repo"),
                paper_info=paper_info,
                code_files_info=code_files_info,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.debug(response)
        return response
