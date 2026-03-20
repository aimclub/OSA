import asyncio
import os

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import OperationEvent, EventKind
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
    Validates scientific papers in PDF format by cross-referencing content with associated code repositories to ensure consistency and accuracy between documented research and implemented code.
    
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
            git_agent: An agent for interacting with a Git platform, used for repository operations such as creating pull requests.
            create_fork: If True, the validator will create a fork of the target repository as part of its operation. This is typically set when the goal is to submit changes via a pull request from a forked copy.
            attachment: Optional path to a PDF file containing the academic paper or article to be validated. If provided, the validator will analyze this document.
        
        Why:
        - The `config_manager` is used to load the specific LLM configuration for the "validation" task and to retrieve all necessary prompt templates.
        - The `git_agent` is required to perform repository-level actions, such as creating forks or pull requests, which are part of the validation workflow.
        - The `create_fork` flag controls whether repository modifications are made directly or through a forked copy, which is essential for contributing to projects where the user lacks direct write access.
        - If an `attachment` is provided, its content is analyzed to validate claims or code references against the actual repository code.
        
        The constructor also initializes internal components:
        - A `CodeAnalyzer` for examining repository source code.
        - A `ModelHandler` configured specifically for validation tasks, built using settings from the `config_manager`.
        - A `PromptLoader` to access the prompt templates needed for the validation process.
        - An internal list (`events`) to log operation events during validation.
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
        """
        Runs the paper validation process and generates a report if validation succeeds.
        
        This method orchestrates the validation of a scientific paper, generates a PDF report
        if validation returns content, and optionally uploads the report to a Git branch.
        It tracks operation events throughout the process.
        
        The method first calls the asynchronous `validate` method to obtain a structured validation result.
        If content is returned, a PDF report is generated and saved locally. When `create_fork` is enabled
        and the report file exists, it is uploaded to a dedicated branch in the repository.
        If validation returns no content, a warning is logged and report generation is skipped.
        Any `ValueError` raised during validation is caught and recorded as a failure event.
        
        Args:
            None.
        
        Returns:
            dict: A dictionary containing the operation result and a list of events.
                The 'result' key contains:
                    - A dictionary with key "report" and the generated filename (if validation succeeded and a report was created).
                    - None (if validation returned no content).
                    - A dictionary with key "error" and the error message (if a ValueError occurred).
                The 'events' key contains a list of OperationEvent objects recorded during execution.
        """
        try:
            content = asyncio.run(self.validate())
            if content:
                va_re_gen = ValidationReportGenerator(self.config_manager, self.git_agent.metadata)
                va_re_gen.build_pdf("Paper", content)
                self.events.append(OperationEvent(kind=EventKind.GENERATED, target=va_re_gen.filename))
                if self.create_fork and os.path.exists(va_re_gen.output_path):
                    self.git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                    self.events.append(OperationEvent(kind=EventKind.UPLOADED, target=va_re_gen.filename))

                return {"result": {"report": va_re_gen.filename}, "events": self.events}
            else:
                logger.warning("Paper validation returned no content. Skipping report generation.")
                self.events.append(
                    OperationEvent(kind=EventKind.SKIPPED, target="Paper validation", data={"reason": "no content"})
                )
                return {"result": None, "events": self.events}
        except ValueError as e:
            self.events.append(OperationEvent(kind=EventKind.FAILED, target="Paper validation", data={"error": str(e)}))
            return {"result": {"error": str(e)}, "events": self.events}

    async def validate(self) -> dict | None:
        """
        Asynchronously validate a scientific paper against the code repository.
        
        This method orchestrates the full validation pipeline: it processes the paper, analyzes the repository's code files, and then uses a language model to compare the two. The result is a structured validation report. If any step fails, the method logs the error and returns None to allow graceful error handling.
        
        Args:
            None. The method uses the instance's `article` attribute (the path to the paper PDF) and the configured `code_analyzer`.
        
        Returns:
            dict | None: Validation result from the language model, parsed as a dictionary, or None if an error occurs during the validation process.
        
        Raises:
            ValueError: If the article path is missing (i.e., `self.article` is not set).
            Exception: Propagates any unexpected exception that occurs during the validation steps (e.g., from helper methods like `process_paper`, `get_code_files`, `process_code_files`, or `validate_paper_against_repo`). These are caught internally, logged, and result in a return value of None.
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
        
        This method orchestrates the full pipeline: it locates the PDF file, extracts its raw text,
        and then uses a language model to parse and structure the content into a defined JSON format.
        The process is designed to convert a raw PDF into a structured, machine-readable representation
        suitable for downstream validation and analysis tasks.
        
        Args:
            None. The method uses the instance's `article` attribute (presumably containing a PDF source)
            and configured `model_handler` and `prompts`.
        
        Returns:
            str: The processed paper content. This is the JSON string response from the language model,
            which contains the extracted and structured sections of the paper.
        
        Raises:
            ValueError: If the PDF source referenced by `self.article` is invalid or cannot be located.
            JsonParseError: If the language model's response cannot be parsed into valid JSON.
            ValidationError: If the parsed JSON fails pydantic validation.
            PromptBuilderError: If an error occurs while rendering the prompt template.
            (Note: The latter three exceptions propagate from the helper methods `async_send_and_parse`,
            `JsonProcessor.parse`, and `PromptBuilder.render` respectively.)
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
        
        This method sends a validation prompt to a language model, comparing the paper information with the aggregated code analysis. The prompt is rendered from a template, and the model's response is parsed as JSON. If parsing fails, the request is retried according to the model handler's retry policy.
        
        Args:
            paper_info: Processed paper information, typically a summary or extracted details from an academic paper.
            code_files_info: Aggregated analysis of code files from the repository, such as structure, key functions, or metadata.
        
        Returns:
            dict: Validation result from the language model, parsed as a JSON object. The content and structure of this dictionary depend on the specific validation prompt and the model's response.
        
        Raises:
            JsonParseError: If the model's response cannot be parsed as JSON after all retry attempts.
            ValidationError: If pydantic validation of the parsed response fails after all retries.
            PromptBuilderError: If an error occurs while rendering the validation prompt template.
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
