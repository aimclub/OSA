import os
import re
import requests
from typing import List, Optional
from tempfile import NamedTemporaryFile
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.readmeai.ingestion.models import RepositoryContext
from osa_tool.readmeai.logger import get_logger

_logger = get_logger(__name__)


class ArticleFinder:
    """Collects all paths to supposed articles"""

    def __init__(self, config: ArticleConfigLoader, repo_context: RepositoryContext, pdf_source: Optional[str] = None) -> None:
        self.config: ArticleConfigLoader = config
        self.docs: List[str] = repo_context.docs_paths
        self.pdf_source: Optional[str] = pdf_source

    @property
    def get_pdf_paths(self) -> List[str]:
        """
        Collects all paths to PDF files from:
        - Local files ending with .pdf
        - PDF files found in one or more readme.md
        - PDF file from the provided URL (if available) or file path
        """
        '''
        pdf_paths = [f"{self.config.git.name}/{path}" for path in self.docs if path.endswith(".pdf")]
        
        readme_paths = [f"{self.config.git.name}/{path}" for path in self.docs if path.lower().endswith("readme.md")]
        for readme_path in readme_paths:
            pdf_links = self.extract_pdf_links_from_readme(readme_path)
            pdf_paths.extend(pdf_links)
        '''

        pdf_paths = []
        if self.pdf_source:
            if self.pdf_source.lower().startswith("http"):
                pdf_file = self.fetch_pdf_from_url(self.pdf_source)
                if pdf_file:
                    pdf_paths.append(pdf_file)
            elif os.path.isfile(self.pdf_source) and self.pdf_source.lower().endswith('.pdf'):
                pdf_paths.append(self.pdf_source)
        return pdf_paths

    def extract_pdf_links_from_readme(self, readme_path: str) -> List[str]:
        """
        Extracts all links from readme.md and checks if they are PDFs.
        If a link is a PDF, downloads and saves it.
        """
        pdf_paths = []
        url_pattern = re.compile(r'https?://\S+')

        try:
            with open(readme_path, 'r', encoding='utf-8') as readme_file:
                for line in readme_file:
                    urls = url_pattern.findall(line)
                    for url in urls:
                        pdf_file = self.fetch_pdf_from_url(url)
                        if pdf_file:
                            pdf_paths.append(pdf_file)
        except Exception as e:
            _logger.error(f"Error while reading {readme_path}", exc_info=True)

        return pdf_paths

    @staticmethod
    def fetch_pdf_from_url(url: str) -> Optional[str]:
        """
        Checks if the given URL returns a PDF file. If so, saves it
        to a temporary file and returns the path.
        """
        try:
            response = requests.get(url, stream=True, timeout=10)
            content_type = response.headers.get('Content-Type', '')

            if response.status_code == 200 and 'application/pdf' in content_type.lower():
                temp_pdf = NamedTemporaryFile(delete=False, suffix=".pdf", prefix="downloaded_", dir=os.getcwd())
                with open(temp_pdf.name, 'wb') as pdf_file:
                    for chunk in response.iter_content(chunk_size=8192):
                        pdf_file.write(chunk)

                return temp_pdf.name

        except requests.exceptions.RequestException as e:
            _logger.error(f"Error accessing {url}", exc_info=True)

        return None
