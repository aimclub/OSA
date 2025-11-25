from pathlib import Path

from rich.progress import track

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.conversion.notebook_converter import NotebookConverter
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.utils import read_file
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.utils import parse_folder_name


class CodeAnalyzer:
    """
    Analyzes code files in a repository using a language model.

    This class handles the retrieval and processing of code files from a repository,
    including conversion of Jupyter notebooks to Python scripts, filtering ignored files,
    and sending code content to a model for analysis.
    """

    def __init__(self, config_loader: ConfigLoader, prompts: PromptLoader):
        """
        Initialize the CodeAnalyzer.

        Args:
            config_loader (ConfigLoader): Loader containing configuration settings.
        """
        self.config = config_loader.config
        self.prompts = prompts
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.notebook_convertor = NotebookConverter()
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree

    def get_code_files(self) -> list[str]:
        """
        Retrieve a list of code files from the repository.

        Converts Jupyter notebooks to Python scripts and filters out ignored files.

        Returns:
            list[str]: List of absolute paths to code files.
        """
        repo_path = Path(parse_folder_name(str(self.config.git.repository))).resolve()
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

    def process_code_files(self, code_files: list[str]) -> str:
        """
        Analyze the content of code files using the language model.

        Args:
            code_files (list[str]): List of code file paths.

        Returns:
            str: Aggregated analysis results for all code files.
        """
        result = ""
        for file in track(code_files, description="Analyzing repository files..."):
            logger.debug(f"Getting {file} content ...")
            file_content = read_file(file)
            logger.info(f"Analyzing {file} ...")
            response = self.model_handler.send_request(
                PromptBuilder.render(
                    self.prompts.get("validation.analyze_code_file"),
                    file_content=file_content,
                )
            )
            logger.debug(response)
            file_data = response
            result += file_data + "\n"
        return result
