import asyncio
import base64
import json
import re

import docx2txt

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.validation.analyze.code_analyzer import CodeAnalyzer
from osa_tool.validation.analyze.paper_analyzer import PaperAnalyzer
from osa_tool.validation.experiment import Experiment


class DocValidator:
    """
    Validates documentation files against the code repository.

    This class processes documentation files (DOCX or PDF), extracts and preprocesses their content,
    analyzes code files in the repository, and validates the documentation against the codebase using a language model.
    """

    def __init__(self, config_loader: ConfigLoader):
        """
        Initialize the DocValidator.

        Args:
            config_loader (ConfigLoader): Loader containing configuration settings.
        """
        self.__config = config_loader.config
        self.__prompts = self.__config.prompts
        self.__code_analyzer = CodeAnalyzer(config_loader)
        self.__paper_analyzer = PaperAnalyzer(config_loader, self.__prompts)
        self.__model_handler: ModelHandler = ModelHandlerFactory.build(self.__config)
        self.__experiments = None

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
        response = self.__model_handler.send_and_parse(
            prompt=json.dumps(prompt),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        logger.info(response)

    def _encode_image(self, image_path: str):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    async def validate(self, article_path: str | None) -> tuple[Experiment, ...] | None:
        """
        Asynchronously validate a documentation file against the code repository.

        Args:
            article_path (str): Path to the documentation file (.docx or .pdf) or None.

        Returns:
            dict | None: Validation result from the language model or None if an error occurred.
        """
        if not article_path:
            raise ValueError("Article is missing! Please pass it using --attachment argument.")
        try:
            experiments_list = await self.__paper_analyzer.process_paper(article_path)
            self.__experiments = tuple(Experiment(experiment_descr) for experiment_descr in experiments_list)
            code_files = await asyncio.to_thread(self.__code_analyzer.get_code_files)
            code_files_info = await self.__code_analyzer.process_code_files(code_files)

            await self.__validate_doc_against_repo(code_files_info)
            return self.__experiments
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")
            return None

    def _process_multiple_docs(self):
        pass

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

    async def __validate_doc_against_repo(self, code_files_info: str):
        """
        Asynchronously validate the processed document content against the code repository.

        Args:
            code_files_info (str): Aggregated code files analysis.

        Returns:
            dict: Validation result from the language model.
        """
        logger.info("Validating doc against repository ...")
        for experiment in self.__experiments:
            experiment_assessment = await self.__model_handler.async_send_and_parse(
                PromptBuilder.render(
                    self.__prompts.get("validation.validate_single_experiment"),
                    experiment_description=experiment.description_from_paper,
                    code_files_info=code_files_info,
                ),
                parser=lambda raw: JsonProcessor.parse(raw),
            )
            experiment.assessment = experiment_assessment["assessment"]
            experiment.correspondence_percent = experiment_assessment["correlation_percent"]
