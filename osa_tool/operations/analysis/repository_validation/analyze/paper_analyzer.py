import asyncio

import docx2txt

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandlerFactory, ModelHandler
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.response_cleaner import JsonProcessor


class PaperAnalyzer:

    def __init__(self, config_manager: ConfigManager, prompts: PromptLoader):
        self.__config = config_manager
        self.__prompts = prompts
        model_settings = config_manager.get_model_settings("validation")
        self.__model_handler: ModelHandler = ModelHandlerFactory.build(model_settings)

    async def process_paper(self, document_path: str) -> list[str]:
        """
        Asynchronously extract and process content from a scientific paper (PDF).

        Args:
            document_path (str): Path to the paper PDF file.

        Returns:
            list[str]: Processed paper content.

        Raises:
            ValueError: If the PDF source is invalid.
        """
        if document_path.endswith(".docx"):
            logger.info("Processing DOCX...")
            raw_content = await asyncio.to_thread(self.__parse_docx, document_path)
        elif document_path.endswith(".pdf"):
            logger.info("Processing PDF...")
            raw_content = await asyncio.to_thread(self.__parse_pdf, document_path)
        else:
            raise ValueError(f"Unprocessable file format: {document_path}")
        path_to_pdf = get_pdf_path(document_path)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Sending request to extract experiments section...")
        experiments = await self.__model_handler.async_send_and_parse(
            PromptBuilder.render(
                self.__prompts.get("validation.extract_paper_experiments_list"),
                paper_content=raw_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        experiments_list = experiments["experiment_list"]
        logger.info(f"Found {len(experiments_list)} experiment(s) described in the paper.")
        return experiments_list

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
