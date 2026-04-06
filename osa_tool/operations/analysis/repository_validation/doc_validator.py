import asyncio
import base64
import json
import os

from rich.progress import track

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.operations.analysis.repository_validation.analyze.paper_analyzer import (
    PaperAnalyzer,
)
from osa_tool.operations.analysis.repository_validation.code_analyzer import (
    CodeAnalyzer,
)
from osa_tool.operations.analysis.repository_validation.experiment import Experiment
from osa_tool.operations.analysis.repository_validation.report_generator import (
    ReportGenerator as ValidationReportGenerator,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor


class DocValidator:
    """
    Validates documentation files against the code repository.

    This class processes documentation files (DOCX or PDF), extracts and preprocesses their content,
    analyzes code files in the repository, and validates the documentation against the codebase using a language model.
    """

    def __init__(
        self, config_manager: ConfigManager, git_agent: GitAgent, create_fork: bool, attachment: str | None = None
    ):
        """
        Initialize the DocValidator.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            git_agent (GitAgent): Abstract base class for Git platform agents.
            create_fork (bool): The flag is responsible for creating a pull request.
            attachment (str): Path to the documentation file (.docx or .pdf) or None.
        """
        self.__config_manager = config_manager
        self.__git_agent = git_agent
        self.__create_fork = create_fork
        self.__path_to_doc = attachment
        self.__events: list[OperationEvent] = []

        self.__prompts = self.__config_manager.get_prompts()
        model_settings = self.__config_manager.get_model_settings("validation")
        self.__model_handler: ModelHandler = ModelHandlerFactory.build(model_settings)

        self.__code_analyzer = CodeAnalyzer(config_manager)
        self.__paper_analyzer = PaperAnalyzer(config_manager, self.__prompts)
        self.__experiments = None

    def run(self) -> dict:
        try:
            return asyncio.run(self._run_async())
        except ValueError as e:
            self.__events.append(
                OperationEvent(kind=EventKind.FAILED, target="Document validation", data={"error": str(e)})
            )
            return {"result": {"error": str(e)}, "events": self.__events}

    async def _run_async(self) -> dict:
        content = await self.validate()
        if content:
            va_re_gen = ValidationReportGenerator(self.__config_manager, self.__git_agent.metadata)
            va_re_gen.build_pdf("Document", content)

            self.__events.append(OperationEvent(kind=EventKind.GENERATED, target=va_re_gen.filename))

            if self.__create_fork and os.path.exists(va_re_gen.output_path):
                self.__git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                self.__events.append(OperationEvent(kind=EventKind.UPLOADED, target=va_re_gen.filename))

            return {"result": {"report": va_re_gen.filename}, "events": self.__events}
        logger.warning("Document validation returned no content. Skipping report generation.")
        self.__events.append(
            OperationEvent(
                kind=EventKind.SKIPPED,
                target="Document validation",
                data={"reason": "no content"},
            )
        )
        return {"result": None, "events": self.__events}

    async def validate(self) -> tuple[Experiment, ...]:
        """
        Asynchronously validate a documentation file against the code repository.

        Returns:
            dict: Validation result from the language model.
        """
        if not self.__path_to_doc:
            raise ValueError("Document is missing! Please pass it using --attachment argument.")
        try:
            experiments_list = await self.__paper_analyzer.process_paper(self.__path_to_doc)
            self.__experiments = tuple(Experiment(experiment_descr) for experiment_descr in experiments_list)
            code_files = await asyncio.to_thread(self.__code_analyzer.get_code_files)
            code_files_info = await self.__code_analyzer.process_code_files(code_files)

            await self.__validate_doc_against_repo(code_files_info)
            return self.__experiments
        except Exception as e:
            logger.error(f"Error while validating doc against repo: {e}")
            raise

    async def __validate_doc_against_repo(self, code_files_info: str) -> None:
        """
        Asynchronously validate the processed document content against the code repository.

        Args:
            code_files_info (str): Aggregated code files analysis.
        """
        logger.info("Validating doc against repository ...")
        for experiment in track(self.__experiments, description="Assessing experiments"):
            experiment_assessment = await self.__model_handler.async_send_and_parse(
                PromptBuilder.render(
                    self.__prompts.get("validation.validate_single_experiment"),
                    experiment_description=experiment.description_from_paper,
                    code_files_info=code_files_info,
                ),
                parser=lambda raw: JsonProcessor.parse(raw),
            )
            experiment.impl_src_path = experiment_assessment["implemented_in"]
            experiment.missing = experiment_assessment["missing_critical_components"]
            experiment.correspondence_percent = experiment_assessment["correlation_percent"]
