from pathlib import Path

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.conversion.notebook_converter import NotebookConverter
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.utils import read_file
from osa_tool.utils import logger, parse_folder_name
from osa_tool.validation.prompt_builder import PromptBuilder


class CodeAnalyzer:
    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.notebook_convertor = NotebookConverter()
        self.prompts = PromptBuilder()
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree

    def get_code_files(self) -> list[str]:
        repo_path = Path(parse_folder_name(str(self.config.git.repository))).resolve()
        code_files = []
        logger.info("Getting code files ...")
        for filename in self.tree.split("\n"):
            if self._is_file_ignored(filename):
                logger.debug(f"File '{filename}' is ignored")
                continue
            if filename.endswith(".ipynb"):
                logger.info("Found .ipynb file, converting ...")
                self.notebook_convertor.convert_notebook(str(repo_path.joinpath(filename)))
                code_files.append(str(repo_path.joinpath(filename.replace(".ipynb", ".py"))))
            if filename.endswith(".py"):
                code_files.append(str(repo_path.joinpath(filename)))
        logger.debug(code_files)
        return code_files

    def _is_file_ignored(self, filename: str) -> bool:
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
        result = ""
        for file in code_files:
            logger.info(f"Getting {file} content ...")
            file_content = read_file(file)
            logger.info("Analyzing file ...")
            response = self.model_handler.send_request(self.prompts.get_prompt_to_analyze_code_file(file_content))
            logger.debug(response)
            file_data = response
            result += file_data + "\n"
        return result
