import asyncio

import docx2txt
import tiktoken
from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.operations.docs.readme_generation.inputs.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.inputs.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.operations.analysis.repository_validation.models import ExtractedExperimentsResult


class PaperAnalyzer:

    def __init__(self, config_manager: ConfigManager, prompts: PromptLoader):
        self.__config = config_manager
        self.__prompts = prompts
        model_settings = self.__config.get_model_settings("validation")
        self.__model_handler: ModelHandler = ModelHandlerFactory.build(model_settings)

    async def extract_experiments(self, document_path: str) -> list[str]:
        """
        Asynchronously extract and process content from a scientific paper.

        Args:
            document_path (str): Path to the paper PDF file.

        Returns:
            list[str]: Processed paper content.

        Raises:
            ValueError: If the document source is invalid.
        """
        if document_path.endswith(".docx"):
            logger.info("Processing DOCX...")
            raw_content = await asyncio.to_thread(self.__parse_docx, document_path)
        elif document_path.endswith(".pdf"):
            path_to_pdf = get_pdf_path(document_path)
            if not path_to_pdf:
                raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
            logger.info("Processing PDF...")
            raw_content = await asyncio.to_thread(self.__parse_pdf, document_path)
        else:
            raise ValueError(f"Unprocessable file format: {document_path}")

        logger.info("Sending request to extract experiments section...")
        experiments_list = []
        try:
            raw_experiments = await self.__model_handler.async_send_and_parse(
                PromptBuilder.render(
                    self.__prompts.get("validation.extract_paper_experiments_list"),
                    paper_content=raw_content,
                ),
                parser=lambda raw: JsonProcessor.parse(raw),
            )
            experiments_list = ExtractedExperimentsResult.model_validate(raw_experiments).experiment_list
        except Exception as e:
            logger.warning(f"Structured extraction failed: {e}. Attempting fallback extraction...")
            experiments_list = self.__fallback_extract_experiments(raw_content)

        if not experiments_list:
            logger.warning("Structured extraction returned empty. Attempting fallback extraction...")
            experiments_list = self.__fallback_extract_experiments(raw_content)

        if experiments_list:
            logger.info(f"Found {len(experiments_list)} experiment(s) described in the paper.")
        else:
            logger.warning("No experiments were found in the provided document.")
        return experiments_list

    def __fallback_extract_experiments(self, content: str) -> list[str]:
        """
        Fallback extraction when LLM fails: split by experiment keywords and return paragraphs.
        Returns at least 1 synthetic experiment from the content if nothing found.
        """
        import re

        keywords = r"(experiment|evaluation|test|analysis|methodology|procedure|method|validation)"
        paragraphs = content.split("\n\n")
        experiments = []
        for para in paragraphs:
            if re.search(keywords, para, re.IGNORECASE) and len(para.strip()) > 50:
                experiments.append(para.strip()[:500])
                if len(experiments) >= 2:
                    break
        if not experiments and content.strip():
            experiments = [content.strip()[:500]]
        return experiments

    def __parse_docx(self, path_to_doc: str) -> str:
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

    def __parse_pdf(self, path_to_doc: str) -> str:
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
