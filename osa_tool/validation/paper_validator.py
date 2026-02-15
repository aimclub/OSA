import asyncio

from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from rich.progress import track

from osa_tool.config.settings import ConfigManager
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.validation.analyze.code_analyzer import CodeAnalyzer
from osa_tool.validation.analyze.paper_analyzer import PaperAnalyzer
from osa_tool.validation.experiment import Experiment


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
        self.__config_manager = config_manager
        self.__prompts = self.__config_manager.get_prompts()
        self.__code_analyzer = CodeAnalyzer(config_manager)
        self.__paper_analyzer = PaperAnalyzer(config_manager, self.__prompts)
        model_settings = config_manager.get_model_settings("validation")
        self.__model_handler: ModelHandler = ModelHandlerFactory.build(model_settings)
        self.__experiments = None

    async def validate(self, article_path: str | None) -> tuple[Experiment, ...] | None:
        """
        Asynchronously validate a scientific paper against the code repository.

        Args:
            article_path (str | None): Path to the paper PDF file.

        Returns:
            dict | None: Validation result from the language model or none if an error occurs.

        Raises:
            ValueError: If the article path is missing.
            Exception: If an error occurs during validation.
        """
        if not article_path:
            raise ValueError("Article is missing! Please pass it using --attachment argument.")
        try:
            experiments_list = await self.__paper_analyzer.process_paper(article_path)
            self.__experiments = tuple(Experiment(experiment_descr) for experiment_descr in experiments_list)
            code_files = await asyncio.to_thread(self.__code_analyzer.get_code_files)
            code_files_info = await self.__code_analyzer.process_code_files(code_files)

            await self.__validate_paper_against_repo(code_files_info)
            return self.__experiments
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")
            return None

    async def __validate_paper_against_repo(self, code_files_info: str):
        """
        Asynchronously validate the processed paper content against the code repository.

        Args:
            code_files_info (str): Aggregated code files analysis.
        """
        logger.info("Validating paper against repository ...")
        for experiment in track(self.__experiments, description="Assessing experiments"):
            experiment_assessment = await self.__model_handler.async_send_and_parse(
                PromptBuilder.render(
                    self.__prompts.get("validation.validate_single_experiment"),
                    experiment_description=experiment.description_from_paper,
                    code_files_info=code_files_info,
                ),
                parser=lambda raw: JsonProcessor.parse(raw),
            )
            experiment.assessment = experiment_assessment["assessment"]
            experiment.correspondence_percent = experiment_assessment["correlation_percent"]
