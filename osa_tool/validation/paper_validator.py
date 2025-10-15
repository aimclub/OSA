from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.utils import logger
from osa_tool.validation.code_analyzer import CodeAnalyzer
from osa_tool.validation.prompt_builder import PromptBuilder


class PaperValidator:
    def __init__(self, config_loader: ConfigLoader):
        self.code_analyzer = CodeAnalyzer(config_loader)
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.prompts = PromptBuilder()

    def validate(self, article:str) -> None:
        try:
            paper_info = self.process_paper(article)
            code_files = self.code_analyzer.get_code_files()
            code_files_info = self.code_analyzer.process_code_files(code_files)
            result = self.validate_paper_against_repo(paper_info, code_files_info)
            logger.info(result)
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")

    def process_paper(self, article: str) -> str:
        logger.info("Loading PDF...")
        path_to_pdf = get_pdf_path(article)
        if not path_to_pdf:
            raise ValueError(f"Invalid PDF source provided: {path_to_pdf}. Could not locate a valid PDF.")
        logger.info("Extracting text from PDF ...")
        pdf_content = PdfParser(path_to_pdf).data_extractor()
        logger.info("Sending request to extract sections ...")
        response = self.model_handler.send_request(self.prompts.get_prompt_to_extract_sections_from_paper(pdf_content))
        logger.debug(response)
        return response

    def validate_paper_against_repo(self, paper_info: str, code_files_info: str) -> str:
        logger.info("Validating paper against repository ...")
        response = self.model_handler.send_request(
            self.prompts.get_prompt_to_validate_paper_against_repo(paper_info, code_files_info)
        )
        logger.debug(response)
        return response
