import asyncio
from pathlib import Path
from typing import Iterable, Iterator

from rich.progress import track

from osa_tool.config.settings import ConfigLoader
from osa_tool.conversion.notebook_converter import NotebookConverter
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.operations.docs.readme_generation.utils import read_file
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
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

    SOURCEFILE_EXTENSIONS_LIST = "py", "c", "cpp"
    IGNORE_LIST = (
        "__init__.py",
        "setup.py",
        "conftest.py",
        "manage.py",
        "migrations",
        "tests",
        "test",
        "test_",
        "__pycache__",
        ".pytest_cache",
        ".pyo",
        ".pyc",
    )

    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize the CodeAnalyzer.

        Args:
            config_loader (ConfigLoader): Loader containing configuration settings.
        """
        self.config = config_loader.config
        self.prompts = self.config.prompts
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.notebook_convertor = NotebookConverter()
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree

    def get_code_files(self) -> Iterator[str]:
        """
        Retrieve a list of code files from the repository.

        Converts Jupyter notebooks to Python scripts and filters out ignored files.

        Returns:
            list[str]: List of absolute paths to code files.
        """
        repo_path = Path(parse_folder_name(str(self.config.git.repository))).resolve()
        for filename in track(self.tree.split("\n"), description="Getting code files ..."):
            if self.__is_blacklisted(filename):
                logger.debug(f"File '{filename}' is ignored. Skipping")
                continue
            if self.__is_sourcefile(filename):
                yield str(repo_path.joinpath(filename))
                continue
            if filename.endswith(".ipynb"):
                logger.debug("Found .ipynb file, converting ...")
                self.notebook_convertor.convert_notebook(str(repo_path.joinpath(filename)))
                yield str(repo_path.joinpath(filename.replace(".ipynb", ".py")))

    @classmethod
    def __is_blacklisted(cls, filename: str) -> bool:
        return any(pattern in filename for pattern in cls.IGNORE_LIST)

    @classmethod
    def __is_sourcefile(cls, filename: str) -> bool:
        return any(filename.endswith(f".{pattern}") for pattern in cls.SOURCEFILE_EXTENSIONS_LIST)

    async def process_code_files(self, code_files: Iterable[str]) -> str:
        """
        Analyze the content of code files using the language model asynchronously.

        Args:
            code_files (Iterable[str]): List of code file paths.

        Returns:
            str: Aggregated analysis results for all code files.
        """
        rate_limit = self.config.llm.rate_limit
        semaphore = asyncio.Semaphore(rate_limit)

        # track - синхронная библиотека, в асинхроне пока будет только logger?
        logger.info(f"Starting async analysis of files with rate limit {rate_limit}...")

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
