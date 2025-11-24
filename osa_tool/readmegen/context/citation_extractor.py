from scholarly import scholarly

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.context.article_content import PdfParser
from osa_tool.readmegen.context.article_path import get_pdf_path
from osa_tool.readmegen.models.llm_service import LLMClient
from osa_tool.utils.prompts_builder import PromptLoader


class CitationExtractor:
    def __init__(
            self, config_loader: ConfigLoader, prompts: PromptLoader, metadata: RepositoryMetadata, article_path: str
        ):
        """
        Initialize the CitationExtractor.

        Args:
            config_loader (ConfigLoader): Loader for application configuration.
            prompts: The batch of prompts to send on llm server endpoint.
            metadata: Git repository metadata.
            article_path (str): Path to the input article (PDF file).
        """
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.prompts = prompts
        self.metadata = metadata
        self.article_path = article_path
        self.llm_client = LLMClient(self.config_loader, self.prompts, self.metadata)

    def get_citation(self):
        """
        Generate a citation for the article.

        This method extracts the article name from the PDF, queries Google Scholar for its bibliographic data,
        and returns the citation text.

        Returns:
            str: Citation text retrieved from Google Scholar.
        """
        article_name = self.get_article_name()
        citation_text = self.get_citation_from_google_scholarly(article_name)
        return citation_text

    def get_article_name(self):
        """
        Extract the article name from the PDF file.

        The method reads the PDF content, sends it to the LLM service,
        and retrieves the article title as identified by the model.

        Returns:
            str: Extracted article title.
        """
        path_to_pdf = get_pdf_path(self.article_path)
        pdf_content = PdfParser(path_to_pdf).data_extractor()
        article_name = self.llm_client.get_article_name(pdf_content)
        return article_name

    @staticmethod
    def get_citation_from_google_scholarly(article_name: str) -> str:
        """
        Retrieve a citation from Google Scholar for the given article.

        Args:
            article_name (str): Title of the article to search for.

        Returns:
            str: Bibliographic data of the first matching result in Google Scholar.
        """
        search_query = scholarly.search_pubs(article_name)
        return next(search_query).bib
