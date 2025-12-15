import base64
import json
import re

import docx2txt

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptLoader, PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.validation.code_analyzer import CodeAnalyzer


class DocValidator:
    """
    Validates documentation files against the code repository.

    This class processes documentation files (DOCX or PDF), extracts and preprocesses their content,
    analyzes code files in the repository, and validates the documentation against the codebase using a language model.
    """

    def __init__(self, config_loader: ConfigLoader, prompts: PromptLoader):
        """
        Initialize the DocValidator.

        Args:
            config_loader (ConfigLoader): Loader containing configuration settings.
        """
        self.code_analyzer = CodeAnalyzer(config_loader, prompts)
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.prompts = prompts

    def _describe_image(self, image_path: str):
        base64_image = self._encode_image(image_path)
        prompt = [
            {"type": "text", "text": "What's in this image?"},
            {
                "type": "image",
                "source_type": "base64",
                "data": base64_image,
                "mime_type": "image/jpeg",
            },
        ]
        response = self.model_handler.send_and_parse(
            prompt=json.dumps(prompt),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.info(response)

    def _encode_image(self, image_path: str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def validate(self, path_to_doc: str | None) -> dict:
        """
        Validate a documentation file against the code repository.

        Args:
            path_to_doc (str): Path to the documentation file (.docx or .pdf).

        Returns:
            str: Validation result from the language model.
        """
        if not path_to_doc:
            raise ValueError("Document is missing! Please pass it using --attachment argument.")
        try:
            # self.describe_image("/home/ilya/OSA/docx2txt-test-dir/image19.jpeg")
            doc_info = self.process_doc(path_to_doc)
            code_files = self.code_analyzer.get_code_files()
            code_files_info = self.code_analyzer.process_code_files(code_files)
            result = self.validate_doc_against_repo(doc_info, code_files_info)
            return result
        except Exception as e:
            logger.error(f"Error while validating doc against repo: {e}")
            raise e

    def process_doc(self, path_to_doc: str) -> str:
        """
        Process and extract content from a documentation file.

        Args:
            path_to_doc (str): Path to the documentation file (.docx or .pdf).

        Returns:
            str: Processed document content.
        """
        if path_to_doc.endswith(".docx"):
            logger.info("Processing DOCX...")
            raw_content = self._parse_docx(path_to_doc)
        elif path_to_doc.endswith(".pdf"):
            logger.info("Processing PDF...")
            raw_content = self._parse_pdf(path_to_doc)
        else:
            raise ValueError(f"Unprocessable file format: {path_to_doc}")
        processed_content = self._preprocess_text(raw_content)
        logger.info("Sending request to process document's content ...")
        response = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("validation.extract_document_sections"),
                doc_content=processed_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.debug(response)
        return response

    def _process_multiple_docs(self):
        pass

    def _parse_docx(self, path_to_doc: str) -> str:
        """
        Extract text content from a DOCX file.

        Args:
            path_to_doc (str): Path to the DOCX file.

        Returns:
            str: Extracted text content.
        """
        logger.info(f"Extracting text from {path_to_doc} ...")
        try:
            docx_content = docx2txt.process(path_to_doc)
        except Exception as e:
            raise Exception(f"Error in parsing .docx: {e}")
        return docx_content

    def _parse_pdf(self, path_to_doc: str) -> str:
        """
        Extract text content from a PDF file.

        Args:
            path_to_doc (str): Path to the PDF file.

        Returns:
            str: Extracted text content.
        """
        path_to_pdf = get_pdf_path(path_to_doc)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Extracting text from PDF ...")
        return PdfParser(path_to_pdf).data_extractor()

    def _preprocess_text(self, raw_text: str) -> str:
        """
        Preprocess extracted text by cleaning and formatting.

        Args:
            raw_text (str): Raw text extracted from the document.

        Returns:
            str: Cleaned and formatted text.
        """
        logger.info("Preprocessing extracted text ...")
        text = re.sub(r"[\u200b\u200c\u200d\xad]", "", raw_text)

        text = re.sub(r"\t", " ", text)  # tab to space
        text = re.sub(r" +", " ", text)  # multiple spaces to one
        text = re.sub(r"\n{3,}", "\n\n", text)  # 3+ newlines to 2
        text = "\n".join(line.strip() for line in text.splitlines())
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def validate_doc_against_repo(self, doc_info: str, code_files_info: str) -> dict:
        """
        Validate the processed document content against the code repository.

        Args:
            doc_info (str): Processed document information.
            code_files_info (str): Aggregated code files analysis.

        Returns:
            str: Validation result from the language model.
        """
        logger.info("Validating doc against repository ...")
        response = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("validation.validate_doc_against_repo"),
                doc_info=doc_info,
                code_files_info=code_files_info,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.debug(response)
        return response
