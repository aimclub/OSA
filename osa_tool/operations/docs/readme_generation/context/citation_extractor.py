from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.operations.docs.readme_generation.models.llm_service import LLMClient
from osa_tool.utils.prompts_builder import PromptLoader


class CitationExtractor:
    """
    CitationExtractor extracts bibliographic citations from PDF articles using LLM services and Google Scholar.
    
        Methods:
            __init__: Initializes the extractor with configuration, prompts, metadata, and article path.
            get_citation: Generates a citation by extracting the article name and querying Google Scholar.
            get_article_name: Extracts the article title from the PDF via LLM processing.
            get_citation_from_google_scholarly: Retrieves bibliographic data from Google Scholar for a given article title.
    
        Attributes:
            config_manager: Provides task-specific LLM settings, repository information, and workflow preferences.
            prompts: Batch of prompts for the LLM server endpoint.
            metadata: Git repository metadata.
            article_path: Path to the input PDF article file.
    """

    def __init__(
        self, config_manager: ConfigManager, prompts: PromptLoader, metadata: RepositoryMetadata, article_path: str
    ):
        """
        Initialize the CitationExtractor.
        
        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            prompts: The batch of prompts to send to the LLM server endpoint.
            metadata: Git repository metadata.
            article_path: Path to the input article (PDF file).
        
        Why:
            This constructor sets up the extractor with necessary components for processing citations from an article. It initializes an LLMClient using the config_manager and metadata to enable communication with the LLM server for citation extraction tasks.
        """
        self.prompts = prompts
        self.metadata = metadata
        self.article_path = article_path
        self.llm_client = LLMClient(config_manager, self.metadata)

    def get_citation(self):
        """
        Generate a citation for the article.
        
        This method extracts the article name from the PDF, queries Google Scholar for its bibliographic data,
        and returns the citation text. This is used within the OSA Tool to provide authoritative citation information for academic content validation and documentation enhancement.
        
        Args:
            None.
        
        Returns:
            str: Citation text retrieved from Google Scholar.
        
        Raises:
            JsonParseError: If JSON parsing fails while extracting the article name.
            ValidationError: If pydantic validation fails while extracting the article name.
            PromptBuilderError: If an error occurs while rendering the prompt template for article name extraction.
        """
        article_name = self.get_article_name()
        citation_text = self.get_citation_from_google_scholarly(article_name)
        return citation_text

    def get_article_name(self):
        """
        Extract the article name from the PDF file.
        
        The method reads the PDF content, sends it to the LLM service,
        and retrieves the article title as identified by the model.
        
        WHY: This method is the primary interface for obtaining the article title from a PDF source, centralizing the steps of PDF path resolution, content extraction, and LLM-based title extraction into a single call.
        
        Args:
            None (uses the instance's `article_path` attribute as the PDF source).
        
        Returns:
            str: Extracted article title.
        
        Raises:
            May propagate exceptions from helper functions, including:
                - FileNotFoundError or network errors from `get_pdf_path`.
                - PDF parsing errors from `PdfParser.data_extractor`.
                - JsonParseError, ValidationError, or PromptBuilderError from `LLMClient.get_article_name`.
        """
        path_to_pdf = get_pdf_path(self.article_path)
        pdf_content = PdfParser(path_to_pdf).data_extractor()
        article_name = self.llm_client.get_article_name(pdf_content)
        return article_name

    @staticmethod
    def get_citation_from_google_scholarly(article_name: str) -> str:
        """
        Retrieve a citation from Google Scholar for the given article.
        
        This method queries Google Scholar using the article title and returns the bibliographic data of the first matching result. It is intended to support academic content validation and documentation enhancement within the OSA Tool by providing authoritative citation information.
        
        Args:
            article_name: Title of the article to search for in Google Scholar.
        
        Returns:
            Bibliographic data of the first matching result from Google Scholar as a string.
        
        Note:
            This method is a static placeholder; actual implementation requires the `scholarly` library and an active internet connection to perform the search.
        """
        pass
        # search_query = scholarly.search_pubs(article_name)
        # return next(search_query).bib
