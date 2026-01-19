import asyncio
from pathlib import Path

from rich.progress import track

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigManager
from osa_tool.conversion.notebook_converter import NotebookConverter
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.operations.docs.readme_generation.utils import read_file
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import parse_folder_name


class CodeAnalyzer:
    """
    Analyzes code files in a repository using a language model.

    This class handles the retrieval and processing of code files from a repository,
    including conversion of Jupyter notebooks to Python scripts, filtering ignored files,
    and sending code content to a model for analysis.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the CodeAnalyzer.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
        """
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings('validation')
        self.prompts = self.config_manager.get_prompts()
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.notebook_convertor = NotebookConverter()
        self.sourcerank = SourceRank(self.config_manager)
        self.tree = self.sourcerank.tree

    def get_code_files(self) -> list[str]:
        """
        Retrieve a list of code files from the repository.

        Converts Jupyter notebooks to Python scripts and filters out ignored files.

        Returns:
            list[str]: List of absolute paths to code files.
        """
        repo_path = Path(parse_folder_name(str(self.config_manager.get_git_settings().repository))).resolve()
        code_files = []
        for filename in track(self.tree.split("\n"), description="Getting code files ..."):
            if self._is_file_ignored(filename):
                logger.debug(f"File '{filename}' is ignored")
                continue
            if filename.endswith(".ipynb"):
                logger.debug("Found .ipynb file, converting ...")
                self.notebook_convertor.convert_notebook(str(repo_path.joinpath(filename)))
                code_files.append(str(repo_path.joinpath(filename.replace(".ipynb", ".py"))))
            if filename.endswith(".py"):
                code_files.append(str(repo_path.joinpath(filename)))
        logger.debug(code_files)
        return code_files

    def _is_file_ignored(self, filename: str) -> bool:
        """
        Check if a file should be ignored based on predefined patterns.

        Args:
            filename (str): Name of the file to check.

        Returns:
            bool: True if the file should be ignored, False otherwise.
        """
        IGNORE_LIST = (
            "__init__.py",
            "setup.py",
            "conftest.py",
            "manage.py",
            "migrations",
            "tests",
            "test",
            "test_" "__pycache__",
            ".pytest_cache",
            ".pyo",
            ".pyc",
        )
        return any(pattern in filename for pattern in IGNORE_LIST)

    async def process_code_files(self, code_files: list[str]) -> str:
        """
        Analyze the content of code files using the language model asynchronously.

        Args:
            code_files (list[str]): List of code file paths.

        Returns:
            str: Aggregated analysis results for all code files.
        """
        rate_limit = self.model_settings.rate_limit
        semaphore = asyncio.Semaphore(rate_limit)

        # track - синхронная библиотека, в асинхроне пока будет только logger?
        logger.info(f"Starting async analysis of {len(code_files)} files with rate limit {rate_limit}...")

        async def _process_single_file(file_path: str) -> str:
            """
            Safely process a single file asynchronously.

            Args:
                file_path (str): File path.

            Returns:
                str: File analysis result.

            """
            async with semaphore:
                try:
                    logger.debug(f"Getting {file_path} content ...")
                    file_content = await asyncio.to_thread(read_file, file_path)
                    logger.info(f"Analyzing {file_path} ...")
                    response = await self.model_handler.async_request(
                        PromptBuilder.render(
                            self.prompts.get("validation.analyze_code_file"),
                            file_content=file_content,
                        )
                    )
                    logger.debug(f"Finished {file_path} analysis")
                    return response
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    return f"Error analyzing {file_path}: {e}"

        tasks = [_process_single_file(file) for file in code_files]
        results = await asyncio.gather(*tasks)
        return "\n".join(results) + "\n"
