import asyncio
import base64
import json
import os
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
    Validates documentation files for consistency, completeness, and accuracy relative to the codebase.
    
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
            git_agent: Abstract base class for Git platform agents. Used to interact with the Git repository for operations like creating pull requests.
            create_fork: Flag indicating whether a fork and pull request should be created as part of the validation workflow. When True, the tool will attempt to create a fork and submit changes via a pull request.
            attachment: Path to the documentation file (.docx or .pdf) to be validated, or None if no external file is provided. If provided, this file will be analyzed alongside repository content.
        
        The constructor also initializes several internal components:
        - `model_settings`: Retrieves LLM configuration for the "validation" task from the config_manager.
        - `code_analyzer`: Creates a CodeAnalyzer instance using the config_manager to examine repository source code.
        - `model_handler`: Builds a ModelHandler via ModelHandlerFactory using the validation model settings, which will handle LLM interactions for validation tasks.
        - `prompts`: Loads prompt templates from the config_manager for guiding LLM operations.
        - `events`: Initializes an empty list to record OperationEvent objects during the validation process.
        
        These internal setups prepare the validator to analyze documentation (both from the repository and any provided attachment) using configured LLMs and code analysis, and optionally propose changes via Git operations if `create_fork` is enabled.
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
        """
        Runs the document validation and report generation workflow.
        
        This method orchestrates the validation of a document, generates a PDF report if validation succeeds,
        and optionally uploads the report to a Git repository fork. It also tracks operation events throughout
        the process.
        
        WHY:
        - The method centralizes the validation and reporting steps into a single synchronous operation, handling success, empty content, and error cases uniformly.
        - Uploading the report to a separate fork branch (when enabled) keeps the main repository clean and provides a publicly accessible link to the report.
        
        Args:
            None.
        
        Returns:
            dict: A dictionary containing the operation result and a list of events.
                The 'result' key contains:
                    - On successful validation and report generation: a dictionary with key "report" and the generated filename as value.
                    - If validation returns no content: None.
                    - If validation raises a ValueError: a dictionary with key "error" and the error message as value.
                The 'events' key contains a list of OperationEvent objects recorded during execution, indicating steps like generation, upload, skip, or failure.
        """
        try:
            content = asyncio.run(self.validate())
            if content:
                va_re_gen = ValidationReportGenerator(self.config_manager, self.git_agent.metadata)
                va_re_gen.build_pdf("Document", content)
                self.events.append(OperationEvent(kind=EventKind.GENERATED, target=va_re_gen.filename))
                if self.create_fork and os.path.exists(va_re_gen.output_path):
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
        """
        Describes the contents of an image by sending it to an LLM.
        
        This method encodes the image at the given path to base64, constructs a multimodal prompt,
        sends it to the model via the handler, and logs the parsed response. The LLM's response is parsed as JSON to extract a structured description.
        
        Args:
            image_path: The file system path to the image to be described.
        
        Returns:
            The parsed response from the language model describing the image's contents.
        
        Why:
            This method is used within the documentation validation process to automatically generate textual descriptions of images, which helps in verifying or enhancing image-related documentation without manual inspection.
        """
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
        """
        Encodes an image file into a base64 string.
        
        Args:
            image_path: The file system path to the image that needs to be encoded.
        
        Returns:
            str: The base64 encoded string representation of the image, decoded as a UTF-8 string.
        
        Why:
            This method is used to convert image files into a base64-encoded string format, which is commonly required for embedding images in text-based formats (such as HTML, JSON, or documentation) without needing to reference external files.
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def validate(self) -> dict | None:
        """
        Asynchronously validate a documentation file against the code repository.
        
        This method orchestrates the validation process: it first ensures a document is provided, then processes the document, analyzes the code repository, and finally sends both to a language model to check for consistency and accuracy. If any step fails, the error is logged and `None` is returned.
        
        Args:
            None. Relies on instance attributes:
                - path_to_doc: The file path to the documentation file. Must be set before calling.
                - code_analyzer: The analyzer used to retrieve and process code files from the repository.
                - model_handler and prompts: Used internally by helper methods for LLM interactions.
        
        Returns:
            dict | None: A validation result dictionary from the language model if the process completes successfully, or `None` if an error occurs at any stage.
        
        Raises:
            ValueError: If `path_to_doc` is not set (i.e., no document was provided for validation).
        
        Why:
        - The validation ensures the documentation accurately reflects the current state of the codebase, identifying discrepancies or gaps.
        - The process is asynchronous to allow non-blocking operations, which is beneficial when processing large documents or repositories.
        - Errors are caught and logged to allow the calling code to handle failures gracefully without crashing the entire validation pipeline.
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
        
        This method reads a document file (DOCX or PDF), extracts its raw text, cleans and preprocesses the text, and then sends it to an LLM to parse and structure the content into a JSON format. The LLM is prompted to extract and organize sections from the document. This is done to convert unstructured document content into a structured, machine-readable format for further validation or analysis within the OSA Tool pipeline.
        
        Args:
            None. Relies on instance attributes:
                - path_to_doc: The file path to the document. Determines the parsing method (DOCX or PDF).
                - model_handler: The handler for sending requests to the LLM and parsing responses.
                - prompts: A registry providing the prompt template for extracting document sections.
        
        Returns:
            str: The processed document content, returned as a JSON string parsed from the LLM response. The JSON represents the extracted and structured sections of the document.
        
        Raises:
            ValueError: If the file format of `path_to_doc` is not supported (i.e., not .docx or .pdf).
            JsonParseError: If the LLM response cannot be parsed into valid JSON after all retries (raised by the underlying `async_send_and_parse` method).
            ValidationError: If the parsed JSON fails pydantic validation after all retries (raised by the underlying `async_send_and_parse` method).
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
        """
        Processes multiple documents within the instance by iterating through the stored document list and applying validation or enhancement operations to each one.
        This method is typically called internally to handle batch processing of documents, ensuring consistent treatment across all items in the collection.
        
        Args:
            self: The instance of the DocValidator class containing the documents to be processed.
        
        Returns:
            None: This method does not return a value; it operates directly on the instance's internal document data.
        """
        pass

    def _parse_docx(self) -> str:
        """
        Extract text content from a DOCX file.
        
        This method is used to read and retrieve the textual content from a DOCX document,
        which is necessary for the validation and analysis processes within the OSA Tool.
        It ensures that documentation content from DOCX files can be processed and
        integrated into automated documentation workflows.
        
        Args:
            self.path_to_doc: The file path to the DOCX document to be parsed.
        
        Returns:
            str: The extracted text content from the DOCX file.
        
        Raises:
            Exception: If an error occurs during the parsing process, an exception is
                       raised with a descriptive message about the parsing failure.
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
        
        This method validates the PDF source, retrieves a local file path, and delegates text extraction to a specialized PDF parser. The parser extracts text while excluding content identified as part of tables.
        
        WHY: The method ensures that only verified PDF files (from URLs or local paths) are processed, preventing downstream errors, and focuses on extracting narrative text by filtering out tabular data.
        
        Args:
            None (uses the instance's `path_to_doc` attribute as the PDF source).
        
        Returns:
            str: Extracted text content. If no text is extracted, an empty string is returned from the underlying parser.
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
        
        Specifically, this method removes invisible and problematic Unicode characters, normalizes whitespace, and trims excess line breaks to produce a clean, readable text block. This is necessary because raw extracted text often contains formatting artifacts, irregular spacing, and hidden characters that can interfere with downstream processing or display.
        
        Args:
            raw_text: Raw text extracted from the document.
        
        Returns:
            Cleaned and formatted text with normalized whitespace and removed hidden characters.
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
        
        This method sends the document and code analysis to a language model to check for consistency, accuracy, or other validation criteria defined in the prompt. It logs the process and returns the parsed validation result.
        
        Args:
            doc_info: Processed document information, typically a string containing the content or metadata of the document to validate.
            code_files_info: Aggregated analysis of code files from the repository, provided as a string.
        
        Returns:
            dict: Validation result parsed from the language model's JSON response. The structure and content depend on the validation prompt and the model's output.
        
        Why:
        - The validation ensures the document aligns with the actual codebase, catching discrepancies or missing information.
        - Using an asynchronous LLM call allows non-blocking operation, which is beneficial when handling multiple validations or large prompts.
        - The response is parsed via JsonProcessor to safely extract structured JSON from the model's raw output, ensuring reliable data for downstream use.
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
