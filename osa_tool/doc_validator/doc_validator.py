from pathlib import Path

import docx2txt

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.convertion.notebook_converter import NotebookConverter
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.readmegen.postprocessor.response_cleaner import process_text
from osa_tool.readmegen.utils import read_file
from osa_tool.utils import logger, parse_folder_name


class PaperValidator:
    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree
        self.notebook_convertor = NotebookConverter()

    def validate(self, doc: str):
        try:
            self.process_doc(doc)
        except Exception as e:
            pass

    def process_doc(self, doc: str):
        logger.info("Extracting text from Docx ...")
        docx_content = docx2txt.process(doc)
        logger.info("Sending request to extract sections ...")
        response = self.model_handler.send_request(article_extract.format(pdf_content=pdf_content))
        logger.debug(response)
        return response
