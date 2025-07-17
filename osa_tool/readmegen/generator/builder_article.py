import json

from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.generator.base_builder import MarkdownBuilderBase


class MarkdownBuilderArticle(MarkdownBuilderBase):
    """
    Builds each section of the README Markdown file for article-like repositories.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        overview: str = None,
        content: str = None,
        algorithms: str = None,
        getting_started: str = None,
    ):
        super().__init__(config_loader, overview=overview, getting_started=getting_started)
        self._content_json = content
        self._algorithms_json = algorithms

    @property
    def content(self) -> str:
        """Generates the README Repository Content section"""
        if not self._content_json:
            return ""
        content_data = json.loads(self._content_json)
        return self._template["content"].format(content_data["content"])

    @property
    def algorithms(self) -> str:
        """Generates the README Algorithms section"""
        if not self._algorithms_json:
            return ""
        algorithms_data = json.loads(self._algorithms_json)
        return self._template["algorithms"].format(algorithms_data["algorithms"])

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

    def build(self):
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
