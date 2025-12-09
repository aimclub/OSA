import asyncio

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptLoader, PromptBuilder
from osa_tool.validation.code_analyzer import CodeAnalyzer


class PaperValidator:
    """
    Validates a scientific paper (PDF) against the code repository.

    This class extracts and processes the content of a paper, analyzes code files in the repository,
    and validates the paper against the codebase using a language model.
    """

    def __init__(self, config_loader: ConfigLoader, prompts: PromptLoader):
        """
        Initialize the PaperValidator.

        Args:
            config_loader (ConfigLoader): Loader containing configuration settings.
        """
        self.code_analyzer = CodeAnalyzer(config_loader, prompts)
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.prompts = prompts

    def validate(self, article: str | None) -> str:
        """
        Validate a scientific paper against the code repository.

        Args:
            article (str | None): Path to the paper PDF file.

        Returns:
            str: Validation result from the language model.

        Raises:
            ValueError: If the article path is missing.
            Exception: If an error occurs during validation.
        """
        if not article:
            raise ValueError("Article is missing! Please pass it using --attachment argument.")
        try:
            paper_info = self.process_paper(article)
            code_files = self.code_analyzer.get_code_files()
            code_files_info = self.code_analyzer.process_code_files(code_files)
            result = self.validate_paper_against_repo(paper_info, code_files_info)
            return result
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")
            raise e

    async def validate_async(self, article: str | None) -> str:
        """
        Asynchronously validate a scientific paper against the code repository.

        Args:
            article (str | None): Path to the paper PDF file.

        Returns:
            str: Validation result from the language model.

        Raises:
            ValueError: If the article path is missing.
            Exception: If an error occurs during validation.
        """
        if not article:
            raise ValueError("Article is missing! Please pass it using --attachment argument.")
        try:
            paper_info = await self.process_paper_async(article)
            code_files = self.code_analyzer.get_code_files()
            code_files_info = await self.code_analyzer.process_code_files_async(code_files)
            result = await self.validate_paper_against_repo_async(paper_info, code_files_info)
            return result
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")
            raise e

    def process_paper(self, article: str) -> str:
        """
        Extract and process content from a scientific paper (PDF).

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
        pdf_content = PdfParser(path_to_pdf).data_extractor()
        logger.info("Sending request to extract sections ...")
        response = self.model_handler.send_request(
            PromptBuilder.render(
                self.prompts.get("validation.extract_paper_section"),
                paper_content=pdf_content,
            )
        )
        logger.debug(response)
        return response

    async def process_paper_async(self, article: str) -> str:
        """
        Asynchronously extract and process content from a scientific paper (PDF).

        Args:
            article (str): Path to the paper PDF file.

        Returns:
            str: Processed paper content.

        Raises:
            ValueError: If the PDF source is invalid.
        """
        loop = asyncio.get_running_loop()
        logger.info("Loading PDF...")
        path_to_pdf = get_pdf_path(article)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Extracting text from PDF ...")
        pdf_content = await loop.run_in_executor(None, lambda: PdfParser(path_to_pdf).data_extractor())
        logger.info("Sending request to extract sections ...")
        response = await self.model_handler.async_request(
            PromptBuilder.render(
                self.prompts.get("validation.extract_paper_section"),
                paper_content=pdf_content,
            )
        )
        logger.debug(response)
        return response

    def validate_paper_against_repo(self, paper_info: str, code_files_info: str) -> str:
        """
        Validate the processed paper content against the code repository.

        Args:
            paper_info (str): Processed paper information.
            code_files_info (str): Aggregated code files analysis.

        Returns:
            str: Validation result from the language model.
        """
        logger.info("Validating paper against repository ...")
        response = self.model_handler.send_request(
            PromptBuilder.render(
                self.prompts.get("validation.validate_paper_against_repo"),
                paper_info=paper_info,
                code_files_info=code_files_info,
            )
        )
        logger.debug(response)
        return response

    async def validate_paper_against_repo_async(self, paper_info: str, code_files_info: str) -> str:
        """
        Asynchronously validate the processed paper content against the code repository.

        Args:
            paper_info (str): Processed paper information.
            code_files_info (str): Aggregated code files analysis.

        Returns:
            str: Validation result from the language model.
        """
        logger.info("Validating paper against repository ...")
        response = await self.model_handler.async_request(
            PromptBuilder.render(
                self.prompts.get("validation.validate_paper_against_repo"),
                paper_info=paper_info,
                code_files_info=code_files_info,
            )
        )
        logger.debug(response)
        return response
