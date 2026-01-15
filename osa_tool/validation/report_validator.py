import asyncio
import base64
import json
import re

import docx2txt

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from sentence_transformers import SentenceTransformer, util

from osa_tool.config.settings import ConfigLoader
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.validation.doc_validator import DocValidator


class ReportValidator(DocValidator):
    """
    Validates report files against the code repository.

    This class processes report files (DOCX or PDF), extracts and preprocesses their content,
    analyzes code files in the repository, and validates the report against the codebase using a language model.
    """

    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize the ReportValidator.

        Args:
            config_loader (ConfigLoader): Loader containing configuration settings.
        """
        super().__init__(config_loader)

    async def _extract_implementation_doc_sections(self, path_to_doc: str) -> str:
        """
        Extract relevant sections from the document text.

        Args:
            path_to_doc: Path to the document file.

        Returns:
            str: The filtered document text.
        """
        converter = DocumentConverter()
        doc = converter.convert(path_to_doc).document
        chunker = HybridChunker()
        chunks = list(chunker.chunk(dl_doc=doc))
        headings = set()
        for chunk in chunks:
            logger.debug(f"Section Headings: {chunk.meta.headings}")
            headings.update(chunk.meta.headings)

        # TODO: move to constants
        model = SentenceTransformer("all-mpnet-base-v2")
        target_labels = [
            "Методы",
            "Методология",
            "Реализация",
            "Подход",
            "Эксперименты",
            "Оценка",
            "Результаты",
            "Анализ",
        ]
        threshold = 0.6

        titles = list(headings)
        title_embs = model.encode(titles, convert_to_tensor=True, normalize_embeddings=True)
        label_embs = model.encode(target_labels, convert_to_tensor=True, normalize_embeddings=True)
        scores = util.cos_sim(title_embs, label_embs)
        max_scores, max_idx = scores.max(dim=1)

        filtered_sections = [titles[i] for i in range(len(titles)) if max_scores[i] >= threshold]
        result = ""
        for chunk in chunks:
            if any(heading in filtered_sections for heading in chunk.meta.headings):
                result += chunk.text
        return result

    async def process_doc(self, path_to_doc: str) -> str:
        """
        Process and extract content from a documentation file asynchronously.

        Args:
            path_to_doc (str): Path to the documentation file (.docx or .pdf).

        Returns:
            str: Processed document content.
        """
        # TODO: provide proper exceptions for unsupported formats
        logger.info("Extracting relevant document sections ...")
        filtered_content = await self._extract_implementation_doc_sections(path_to_doc)
        logger.info(f"Reduced to {len(filtered_content)}.")

        return filtered_content

    async def validate_doc_against_repo(self, doc_info: str, code_files_info: str) -> str:
        """
        Asynchronously validate the processed document content against the code repository.

        Args:
            doc_info (str): Processed document information.
            code_files_info (str): Aggregated code files analysis.

        Returns:
            str: Validation result from the language model.
        """
        logger.info("Validating doc against repository ...")
        response = await self.model_handler.async_send_and_parse(
            PromptBuilder.render(
                self.prompts.get("validation.validate_report_against_repo"),
                doc_info=doc_info,
                code_files_info=code_files_info,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.debug(response)
        return response
