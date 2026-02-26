import asyncio

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import OperationEvent
from osa_tool.operations.analysis.repository_validation.code_analyzer import CodeAnalyzer
from osa_tool.operations.analysis.repository_validation.report_generator import (
    ReportGenerator as ValidationReportGenerator,
)
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor


class PaperValidator:
    """
    Validates a scientific paper (PDF) against the code repository.

    This class extracts and processes the content of a paper, analyzes code files in the repository,
    and validates the paper against the codebase using a language model.
    """

    def __init__(
        self, config_manager: ConfigManager, git_agent: GitAgent, create_fork: bool, attachment: str | None = None
    ):
        """
        Initialize the PaperValidator.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            git_agent (GitAgent): Abstract base class for Git platform agents.
            create_fork (bool): The flag is responsible for creating a pull request.
            attachment (str | None): Path to the paper PDF file.
        """
        self.config_manager = config_manager
        self.git_agent = git_agent
        self.create_fork = create_fork
        self.article = attachment
        self.code_analyzer = CodeAnalyzer(config_manager)
        self.model_settings = config_manager.get_model_settings("validation")
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.prompts = self.config_manager.get_prompts()
        self.events: list[OperationEvent] = []

    def run(self) -> dict:
        try:
            content = asyncio.run(self.validate())
            if content:
                va_re_gen = ValidationReportGenerator(self.config_manager, self.git_agent.metadata)
                va_re_gen.build_pdf("Paper", content)
                if self.create_fork:
                    self.git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)

                return {"result": "", "events": self.events}
            else:
                logger.warning("Paper validation returned no content. Skipping report generation.")
                return {"result": None, "events": self.events}
        except ValueError as e:
            return {"result": {"error": str(e)}, "events": self.events}

    async def validate(self) -> dict | None:
        """
        Asynchronously validate a scientific paper against the code repository.

        Returns:
            dict | None: Validation result from the language model or none if an error occurs.

        Raises:
            ValueError: If the article path is missing.
            Exception: If an error occurs during validation.
        """
        if not self.article:
            raise ValueError("Article is missing! Please pass it using --attachment argument.")
        try:
            paper_info = await self.process_paper()
            code_files = await asyncio.to_thread(self.code_analyzer.get_code_files)
            code_files_info = await self.code_analyzer.process_code_files(code_files)
            result = await self.validate_paper_against_repo(paper_info, code_files_info)
            return result
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")
            return None

    async def process_paper(self) -> str:
        """
        Asynchronously extract and process content from a scientific paper (PDF).

        Returns:
            str: Processed paper content.

        Raises:
            ValueError: If the PDF source is invalid.
        """
        logger.info("Loading PDF...")
        path_to_pdf = get_pdf_path(self.article)
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
