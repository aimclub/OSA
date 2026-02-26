import asyncio
import base64
import json
import re

import docx2txt

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.analysis.repository_validation.code_analyzer import CodeAnalyzer
from osa_tool.operations.analysis.repository_validation.report_generator import (
    ReportGenerator as ValidationReportGenerator,
)
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor


class DocValidator:
    """
    Validates documentation files against the code repository.

    This class processes documentation files (DOCX or PDF), extracts and preprocesses their content,
    analyzes code files in the repository, and validates the documentation against the codebase using a language model.
    """

    def __init__(
        self, config_manager: ConfigManager, git_agent: GitAgent, create_fork: bool, attachment: str | None = None
    ):
        """
        Initialize the DocValidator.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            git_agent (GitAgent): Abstract base class for Git platform agents.
            create_fork (bool): The flag is responsible for creating a pull request.
            attachment (str): Path to the documentation file (.docx or .pdf) or None.
        """
        self.config_manager = config_manager
        self.git_agent = git_agent
        self.create_fork = create_fork
        self.path_to_doc = attachment
        self.model_settings = self.config_manager.get_model_settings("validation")
        self.code_analyzer = CodeAnalyzer(self.config_manager)
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.prompts = self.config_manager.get_prompts()
        self.events: list[OperationEvent] = []

    def run(self) -> dict:
        try:
            content = asyncio.run(self.validate())
            if content:
                va_re_gen = ValidationReportGenerator(self.config_manager, self.git_agent.metadata)
                va_re_gen.build_pdf("Document", content)
                self.events.append(OperationEvent(kind=EventKind.GENERATED, target=va_re_gen.filename))
                if self.create_fork:
                    self.git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                    self.events.append(OperationEvent(kind=EventKind.UPLOADED, target=va_re_gen.filename))

                return {"result": {"report": va_re_gen.filename}, "events": self.events}
            else:
                logger.warning("Document validation returned no content. Skipping report generation.")
                self.events.append(
                    OperationEvent(kind=EventKind.SKIPPED, target="Document validation", data={"reason": "no content"})
                )
                return {"result": None, "events": self.events}
        except ValueError as e:
            self.events.append(
                OperationEvent(kind=EventKind.FAILED, target="Document validation", data={"error": str(e)})
            )
            return {"result": {"error": str(e)}, "events": self.events}

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

    @staticmethod
    def _encode_image(image_path: str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def validate(self) -> dict | None:
        """
        Asynchronously validate a documentation file against the code repository.

        Returns:
            dict | None: Validation result from the language model or None if an error occurred.
        """
        if not self.path_to_doc:
            raise ValueError("Document is missing! Please pass it using --attachment argument.")
        try:
            doc_info = await self.process_doc()
            code_files = await asyncio.to_thread(self.code_analyzer.get_code_files)
            code_files_info = await self.code_analyzer.process_code_files(code_files)
            result = await self.validate_doc_against_repo(doc_info, code_files_info)
            return result
        except Exception as e:
            logger.error(f"Error while validating doc against repo: {e}")
            return None

    async def process_doc(self) -> str:
        """
        Process and extract content from a documentation file asynchronously.

        Returns:
            str: Processed document content.
        """
        if self.path_to_doc.endswith(".docx"):
            logger.info("Processing DOCX...")
            raw_content = await asyncio.to_thread(self._parse_docx)
        elif self.path_to_doc.endswith(".pdf"):
            logger.info("Processing PDF...")
            raw_content = await asyncio.to_thread(self._parse_pdf)
        else:
            raise ValueError(f"Unprocessable file format: {self.path_to_doc}")
        processed_content = self._preprocess_text(raw_content)
        logger.info("Sending request to process document's content ...")
        response = await self.model_handler.async_send_and_parse(
            PromptBuilder.render(
                self.prompts.get("validation.extract_document_sections"),
                doc_content=processed_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.debug(response)
        return response

    def _process_multiple_docs(self):
        pass

    def _parse_docx(self) -> str:
        """
        Extract text content from a DOCX file.

        Returns:
            str: Extracted text content.
        """
        logger.info(f"Extracting text from {self.path_to_doc} ...")
        try:
            docx_content = docx2txt.process(self.path_to_doc)
        except Exception as e:
            raise Exception(f"Error in parsing .docx: {e}")
        return docx_content

    def _parse_pdf(self) -> str:
        """
        Extract text content from a PDF file.

        Returns:
            str: Extracted text content.
        """
        path_to_pdf = get_pdf_path(self.path_to_doc)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Extracting text from PDF ...")
        return PdfParser(path_to_pdf).data_extractor()

    @staticmethod
    def _preprocess_text(raw_text: str) -> str:
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

    async def validate_doc_against_repo(self, doc_info: str, code_files_info: str) -> dict:
        """
        Asynchronously validate the processed document content against the code repository.

        Args:
            doc_info (str): Processed document information.
            code_files_info (str): Aggregated code files analysis.

        Returns:
            dict: Validation result from the language model.
        """
        logger.info("Validating doc against repository ...")
        response = await self.model_handler.async_send_and_parse(
            PromptBuilder.render(
                self.prompts.get("validation.validate_doc_against_repo"),
                doc_info=doc_info,
                code_files_info=code_files_info,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.debug(response)
        return response
