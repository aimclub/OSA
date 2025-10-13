import base64
import json
import re
from pathlib import Path

import docx2txt

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.convertion.notebook_converter import NotebookConverter
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.utils import read_file
from osa_tool.utils import logger, parse_folder_name

document_extract = """
INPUT DATA:
{doc_content}

TASK:
Analyze the provided Russian-language documentation text from a scientific or technical project and extract the following sections as plain text:

1. **Abstract** — look for a section titled exactly or similarly to "Реферат". Do NOT use "Введение" (Introduction) as a substitute.
2. **Experiments / Implementation** — look for sections titled "Программная реализация", "Реализация", "Алгоритмы", "Архитектура", "Пример использования", or similar that describe the actual code, system design, or experimental setup.
3. **Results** — look for a section titled "Результаты". Do NOT include "Выводы" (Conclusions) or "Заключение" unless they explicitly contain numerical or empirical results.

Return the extracted content in a JSON object with keys: "abstract", "experiments", and "results".

RULES:
- Return ONLY a valid JSON object—no extra text, markdown, or commentary.
- Preserve the original Russian text exactly as it appears, including line breaks and special characters.
- If a section appears multiple times, concatenate all relevant parts in order of appearance.
- If a section is not found, return an empty string ("").
- Do NOT translate, paraphrase, summarize, or modify the text.
- Do NOT include section headings unless they are part of the original paragraph (e.g., if the text starts with "Результаты: ...", keep it).

OUTPUT FORMAT:
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

validate_doc_against_repo = """
INPUT DATA:
{doc_info}

{code_files_info}

TASK:
Compare the Russian-language documentation (which describes experiments and results) with the actual implementation in the repository code.

Evaluate the following:
- Does the code implement the methods, algorithms, system architecture, or experimental procedures described in the documentation’s "experiments" or "implementation" section?
- Are the datasets, input formats, evaluation metrics, and key parameters consistent between the documentation and the code?
- Can the reported results (e.g., performance numbers, outputs, behaviors) be reproduced using the provided code?

Based on this comparison:
1. Set "correspondence" to `true` if the code substantially implements what the documentation claims; otherwise `false`.
2. Assign a "percentage" score (0.0–100.0) reflecting the degree of alignment (100.0 = full reproducibility and coverage).
3. Write a brief "conclusion" in English explaining the score, citing specific matches or gaps (e.g., missing evaluation script, undocumented preprocessing step).

RULES:
- The documentation is in Russian—analyze its technical meaning directly; do NOT translate it unless necessary for reasoning.
- Return ONLY a valid JSON object—no extra text, markdown, or commentary.
- Use English for the "conclusion" field to ensure consistency in downstream processing.
- If critical components (e.g., training loop, dataset loader, metric calculation) are absent from the code, assign a low percentage.
- Base your judgment exclusively on the provided inputs.

OUTPUT FORMAT:
{{
  "correspondence": bool,
  "percentage": float,
  "conclusion": string
}}
"""


class DocValidator:
    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree
        self.notebook_convertor = NotebookConverter()

    def describe_image(self, image_path: str):
        base64_image = self.encode_image(image_path)
        prompt = [
            {"type": "text", "text": "What's in this image?"},
            {
                "type": "image",
                "source_type": "base64",
                "data": base64_image,
                "mime_type": "image/jpeg",
            },
        ]
        response = self.model_handler.send_request(json.dumps(prompt))
        logger.info(response)

    def encode_image(self, image_path: str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def validate(self, path_to_doc: str):
        try:
            # self.describe_image("/home/ilya/OSA/docx2txt-test-dir/image19.jpeg")
            doc_info = self.process_doc(path_to_doc)
            code_files = self.get_code_files()
            code_files_info = self.process_code_files(code_files)
            result = self.validate_doc_against_repo(doc_info, code_files_info)
            logger.info(result)
        except Exception as e:
            logger.error(e)

    def process_doc(self, path_to_doc: str):
        raw_content = self.parse_docx(path_to_doc)
        processed_content = self._preprocess_text(raw_content)
        logger.info("Sending request to process document's content ...")
        response = self.model_handler.send_request(document_extract.format(doc_content=processed_content))
        logger.debug(response)
        return response

    def process_multiple_docs(self):
        pass

    def parse_docx(self, path_to_docx: str) -> str:
        logger.info(f"Extracting text from {path_to_docx} ...")
        try:
            docx_content = docx2txt.process(path_to_docx)
        except Exception as e:
            raise Exception(f"Error in parsing .docx: {e}")
        return docx_content

    def _preprocess_text(self, raw_text: str) -> str:
        logger.info("Preprocessing extracted text ...")
        text = re.sub(r"[\u200b\u200c\u200d\xad]", "", raw_text)

        text = re.sub(r"\t", " ", text)  # tab to space
        text = re.sub(r" +", " ", text)  # multiple spaces to one
        text = re.sub(r"\n{3,}", "\n\n", text)  # 3+ newlines to 2
        text = "\n".join(line.strip() for line in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

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
        # TODO:
        # 1. Ignore tests
        # 2. Ignore __init__.py?
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

    def validate_doc_against_repo(self, doc_info: str, code_files_info: str):
        logger.info("Validating doc against repository ...")
        response = self.model_handler.send_request(
            validate_doc_against_repo.format(doc_info=doc_info, code_files_info=code_files_info)
        )
        logger.debug(response)
        return response
