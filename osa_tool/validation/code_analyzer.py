from pathlib import Path

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.conversion.notebook_converter import NotebookConverter
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.utils import read_file
from osa_tool.utils import logger, parse_folder_name

file_analyze = """
INPUT DATA:
{file_content}

TASK:
Analyze the attached Python source code file and extract the following information:

1. For each class defined in the file:
   - Class name
   - Its docstring (if present; otherwise an empty string "")
   - A brief description of what the class does (inferred from code if no docstring)
2. For each top-level function defined in the file:
   - Function name
   - List of input argument names (as a list of strings)
   - Return type or description of what it returns (if unclear, write "Not specified")
   - Its docstring (if present; otherwise an empty string "")
   - A brief description of what the function does
3. Provide a high-level description of what the entire file does.

RULES:
- Do NOT include any text outside the JSON object.
- Ensure the output is valid JSON.
- If there are no classes or functions, use empty objects: {{}}.

OUTPUT FORMAT:
Return a valid JSON object with the following structure:

{{
  "description": "string",
  "classes": {{
    "ClassName1": {{
      "docstring": "string or empty",
      "description": "string"}}
    }},
    ...
  }},
  "functions": {{
    "function_name1": {{
      "arguments": ["arg1", "arg2", ...],
      "returns": "description of return value",
      "docstring": "string or empty",
      "description": "string"
    }},
    ...
  }}
}}
"""


class CodeAnalyzer:
    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.notebook_convertor = NotebookConverter()
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree

    def get_code_files(self) -> list[str]:
        # TODO:
        # 1. Ignore tests
        # 2. Ignore __init__.py?
        repo_path = Path(parse_folder_name(str(self.config.git.repository))).resolve()
        code_files = []
        logger.info("Getting code files ...")
        for filename in self.tree.split("\n"):
            if ".ipynb" in filename:
                logger.info("Found .ipynb file, converting ...")
                self.notebook_convertor.convert_notebook(str(repo_path.joinpath(filename)))
                code_files.append(str(repo_path.joinpath(filename.replace(".ipynb", ".py"))))
            if ".py" in filename:
                code_files.append(str(repo_path.joinpath(filename)))
        return code_files

    def process_code_files(self, code_files: list[str]):
        result = ""
        for file in code_files:
            logger.info(f"Getting {file} content ...")
            file_content = read_file(file)
            logger.info("Analyzing file ...")
            response = self.model_handler.send_request(file_analyze.format(file_content=file_content))
            logger.debug(response)
            file_data = response
            result += file_data + "\n"
        return result
