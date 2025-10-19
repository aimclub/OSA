from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.generator.base_builder import MarkdownBuilderBase


class MarkdownBuilderArticle(MarkdownBuilderBase):
    """
    Builds each section of the README Markdown file for article-like repositories.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        metadata: RepositoryMetadata,
        overview: str = None,
        content: str = None,
        algorithms: str = None,
        getting_started: str = None,
    ):
        super().__init__(config_loader, metadata, overview=overview, getting_started=getting_started)
        self._content = content
        self._algorithms = algorithms

    @property
    def content(self) -> str:
        """Generates the README Repository Content section"""
        if not self._content:
            return ""
        return self._template["content"].format(self._content)

    @property
    def algorithms(self) -> str:
        """Generates the README Algorithms section"""
        if not self._algorithms:
            return ""
        return self._template["algorithms"].format(self._algorithms)

    @property
    def toc(self) -> str:
        sections = {
            "Content": self.content,
            "Algorithms": self.algorithms,
            "Installation": self.installation,
            "Getting Started": self.getting_started,
            "License": self.license,
            "Citation": self.citation,
        }
        return self.table_of_contents(sections)

    def build(self) -> str:
        """Builds each section of the README.md file."""
        readme_contents = [
            self.header,
            self.overview,
            self.toc,
            self.content,
            self.algorithms,
            self.installation,
            self.getting_started,
            self.examples,
            self.documentation,
            self.license,
            self.citation,
        ]

        return "\n".join(readme_contents)
