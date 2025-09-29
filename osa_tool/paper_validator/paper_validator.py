from pathlib import Path

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.convertion.notebook_converter import NotebookConverter
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.readmegen.postprocessor.response_cleaner import process_text
from osa_tool.readmegen.utils import read_file
from osa_tool.utils import logger, parse_folder_name

article_extract = """
INPUT DATA:
{pdf_content}

TASK:
Analyze the attached scientific paper and extract the following sections as plain text:

1. The **Abstract** section (usually titled "Abstract").
2. The section describing the **experiments** (may be titled "Experiments", "Experimental Setup", "Methodology", "Materials and Methods", or similar—use your best judgment to identify where the experimental procedures are described).
3. The **Results** section (typically titled "Results", "Findings", or similar—do not include the "Discussion" or "Conclusion" unless they are merged with Results).

Return the extracted text for each section in a JSON object with the keys: "abstract", "experiments", and "results".

RULES:
- Return ONLY a valid JSON object—no additional text, explanations, or formatting.
- For each section:
  - If found, include the full text exactly as it appears (preserving line breaks, equations, BibTeX, DOIs, etc.).
  - If multiple relevant sections exist (e.g., multiple experiment subsections), concatenate them into a single string in logical order.
  - If no such section exists, return an empty string ("").
- Do NOT paraphrase, summarize, or add content.
- Do NOT include section titles unless they appear in the original text.

OUTPUT FORMAT:
Return a valid JSON object with the following structure:

{{
  "abstract": "string",
  "experiments": "string",
  "results": "string"
}}
"""

file_analyze = """
INPUT DATA:
{file_content}

TASK:
Analyze the attached Python source code file and extract the following information:

1. List all import statements (including from ... import ...).
2. For each class defined in the file:
   - Class name
   - Its docstring (if present; otherwise an empty string "")
   - A brief description of what the class does (inferred from code if no docstring)
3. For each top-level function defined in the file:
   - Function name
   - List of input argument names (as a list of strings)
   - Return type or description of what it returns (if unclear, write "Not specified")
   - Its docstring (if present; otherwise an empty string "")
   - A brief description of what the function does
4. Provide a high-level description of what the entire file does.

RULES:
- Do NOT include any text outside the JSON object.
- Ensure the output is valid JSON.
- If there are no classes or functions, use empty objects: {{}}.
- If there are no imports, use an empty list: [].

OUTPUT FORMAT:
Return a valid JSON object with the following structure:

{{
  "description": "string",
  "imports": ["import os", "from typing import List", ...],
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

validate_paper_against_repo = """
INPUT DATA:
{paper_info}

{code_files_info}

TASK:
Compare the scientific paper's described experiments and results with the actual implementation and experimental code in the repository.

Specifically:
- Does the code implement the methods, models, or algorithms described in the paper's experiments section?
- Are the datasets, evaluation metrics, and experimental procedures consistent with those reported?
- Are the results (e.g., numerical outcomes, figures, tables) reproducible from the provided code?

Based on this comparison:
1. Determine if there is substantial compliance between the paper and the code (`true` for compliant, `false` otherwise).
2. Assign a percentage score (0.0 to 100.0) reflecting how well the repository code aligns with the paper’s experimental claims.
3. Provide a concise justification for your assessment.

RULES:
- Return ONLY a valid JSON object—no additional text, markdown, or explanations.
- The percentage must be a float between 0.0 and 100.0.
- If key experimental details are missing from the code (e.g., no training script, no evaluation), reflect this in a low score.
- Base your judgment solely on the provided paper excerpts and code analysis.

OUTPUT FORMAT:
{{
  "correspondence": bool,
  "percentage": float,
  "conclusion": str
}}
"""


class PaperValidator:
    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree
        self.notebook_convertor = NotebookConverter()

    def validate(self, article:str) -> None:
        try:
            paper_info = self.process_paper(article)
            code_files = self.get_code_files()
            code_files_info = self.process_code_files(code_files)
            result = self.validate_paper_against_repo(paper_info, code_files_info)
            logger.info(result)
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")

    def process_paper(self, article: str):
        logger.info("Loading PDF...")
        path_to_pdf = get_pdf_path(article)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Extracting text from PDF ...")
        pdf_content = PdfParser(path_to_pdf).data_extractor()
        logger.info("Sending request to extract sections ...")
        response = self.model_handler.send_request(article_extract.format(pdf_content=pdf_content))
        logger.debug(response)
        return response

    def get_code_files(self) -> list[str]:
        repo_path = Path(parse_folder_name(self.config.git.repository)).resolve()
        code_files = []
        logger.info("Getting code files ...")
        for filename in self.tree.split("\n"):
            if ".ipynb" in filename:
                logger.info("Found .ipynb file, converting ...")
                self.notebook_convertor.convert_notebook(repo_path.joinpath(filename))
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

    def validate_paper_against_repo(self, paper_info, code_files_info):
        logger.info("Validating paper against repository ...")
        response = self.model_handler.send_request(
            validate_paper_against_repo.format(paper_info=paper_info, code_files_info=code_files_info)
        )
        logger.debug(response)
        return response
