import asyncio

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.response_cleaner import JsonProcessor


class PaperAnalyzer:

    def __init__(self, config_loader: ConfigLoader, prompts: PromptLoader):
        self.config = config_loader.config
        self.prompts = prompts
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)

    async def process_paper(self, article_path: str) -> list[str]:
        """
        Asynchronously extract and process content from a scientific paper (PDF).

        Args:
            article_path (str): Path to the paper PDF file.

        Returns:
            list[str]: Processed paper content.

        Raises:
            ValueError: If the PDF source is invalid.
        """
        logger.info("Loading PDF...")
        path_to_pdf = get_pdf_path(article_path)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Extracting text from PDF ...")
        pdf_content = await asyncio.to_thread(PdfParser(path_to_pdf).data_extractor)
        logger.info("Sending request to extract sections ...")
        experiments = await self.model_handler.async_send_and_parse(
            PromptBuilder.render(
                self.prompts.get("validation.extract_paper_experiments_list"),
                paper_content=pdf_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )
        return experiments["experiment_list"]
