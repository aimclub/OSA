import asyncio
import os

import tiktoken
from rich.progress import track

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.operations.analysis.repository_validation.analyze.paper_analyzer import (
    PaperAnalyzer,
)
from osa_tool.operations.analysis.repository_validation.analyze.code_analyzer import (
    CodeAnalyzer,
)
from osa_tool.operations.analysis.repository_validation.models import Experiment, ExperimentValidationResult
from osa_tool.operations.analysis.repository_validation.report_generator import (
    ReportGenerator as ValidationReportGenerator,
)
from osa_tool.operations.analysis.vkr_scoring.vkr_scorer import VkrScorer
from osa_tool.tools.repository_analysis.semantic_retriever import (
    GraphContextRetriever,
    RetrievedContext,
    format_code_snippets,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


class PaperValidator:
    """
    Validates a scientific paper against the code repository.

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
        self.__config_manager = config_manager
        self.__git_agent = git_agent
        self.__create_fork = create_fork
        self.__path_to_article = attachment
        self.__events: list[OperationEvent] = []

        self.__prompts = self.__config_manager.get_prompts()
        self.__model_settings = self.__config_manager.get_model_settings("validation")
        self.__model_handler: ModelHandler = ModelHandlerFactory.build(self.__model_settings)

        self.__code_analyzer = CodeAnalyzer(config_manager)
        self.__paper_analyzer = PaperAnalyzer(config_manager, self.__prompts)
        self.__experiments = []

        self.__vkr_scorer = VkrScorer(config_manager, git_agent)

    def run(self) -> dict:
        try:
            return asyncio.run(self._run_async())
        except ValueError as e:
            self.__events.append(
                OperationEvent(kind=EventKind.FAILED, target="Paper validation", data={"error": str(e)})
            )
            return {"result": {"error": str(e)}, "events": self.__events}

    async def _run_async(self) -> dict:
        content = await self.validate()

        vkr_report = await self.__run_vkr_checks()

        if content:
            va_re_gen = ValidationReportGenerator(self.__config_manager, self.__git_agent.metadata)
            va_re_gen.build_pdf("Paper", content, vkr_report=vkr_report)

            self.__events.append(OperationEvent(kind=EventKind.GENERATED, target=va_re_gen.filename))

            if self.__create_fork and os.path.exists(va_re_gen.output_path):
                self.__git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                self.__events.append(OperationEvent(kind=EventKind.UPLOADED, target=va_re_gen.filename))

            return {"result": {"report": va_re_gen.filename}, "events": self.__events}

        logger.warning("Paper validation returned no content. Skipping report generation.")
        self.__events.append(
            OperationEvent(
                kind=EventKind.SKIPPED,
                target="Paper validation",
                data={"reason": "no content"},
            )
        )
        return {"result": None, "events": self.__events}

    async def __run_vkr_checks(self) -> dict:
        return await asyncio.to_thread(self.__vkr_scorer.get_quality_report)

    async def validate(self) -> list[Experiment]:
        """
        Asynchronously validate a scientific paper against the code repository.

        Returns:
            dict | None: Validation result from the language model or none if an error occurs.

        Raises:
            ValueError: If the article path is missing.
            Exception: If an error occurs during validation.
        """
        if not self.__path_to_article:
            raise ValueError("Article is missing! Please pass it using --attachment argument.")
        try:
            experiments_list = await self.__paper_analyzer.extract_experiments(self.__path_to_article)
            experiment_retriever = GraphContextRetriever(self.__code_analyzer.repo_graph)
            experiments_contexts = experiment_retriever.retrieve(experiments_list)
            await self.__validate_paper_against_repo(experiments_contexts)
            return self.__experiments
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")
            raise

    async def __validate_paper_against_repo(self, llm_prompt_contexts: list[RetrievedContext]):
        """
        Asynchronously compose a validation assessment of the paper content against the code repository.

        Args:
            llm_prompt_contexts (list): Aggregated code files analysis.
        """
        logger.info("Validating paper against repository ...")
        for context in track(llm_prompt_contexts, description="Assessing experiments"):
            code_chunks = format_code_snippets(context.retrieved_nodes)

            prompt = PromptBuilder.render(
                self.__prompts.get("validation.validate_single_experiment_preprocessed"),
                experiment_description=context.query,
                code_snippets=code_chunks,
            )
            experiment_assessment = await self.__model_handler.async_send_and_parse(
                prompt=prompt,
                parser=None,
            )

            input_tokens = tiktoken.get_encoding("cl100k_base").encode(prompt)
            logger.info(f"Tokens used: {len(input_tokens)}")

            raw_pct = experiment_assessment.get("correlation_percent", 0.0)
            try:
                pct = float(raw_pct)
                # LLMs sometimes return 0-100 instead of 0-1; normalise
                if pct > 1.0:
                    pct = pct / 100.0
                pct = max(0.0, min(1.0, pct))
            except (TypeError, ValueError):
                pct = 0.0

            self.__experiments.append(
                Experiment(
                    description_from_paper=context.query,
                    impl_src_path=experiment_assessment.get("implemented_in", []),
                    missing=experiment_assessment.get("missing_critical_components", []),
                    correspondence_percent=pct,
                    reasoning=experiment_assessment.get("reasoning", ""),
                )
            )
