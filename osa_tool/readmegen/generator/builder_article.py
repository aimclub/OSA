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
        """
        Initializes the object with configuration loader and optional JSON content.
        
        Args:
            config_loader: The configuration loader instance used to load settings.
            overview: Optional overview text passed to the base class.
            content: Optional JSON string containing the main content.
            algorithms: Optional JSON string containing algorithm details.
            getting_started: Optional getting started text passed to the base class.
        
        Attributes:
            _content_json: Stores the provided content JSON string.
            _algorithms_json: Stores the provided algorithms JSON string.
        
        Returns:
            None
        """
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
        """
        Return a formatted table of contents for the document.
        
        This property builds a mapping of section titles to the corresponding
        attributes of the instance and delegates rendering to the
        ``table_of_contents`` method. The resulting string is suitable for
        displaying a quick navigation aid for the document.
        
        Args:
            self: The instance whose section attributes are used to build the
                table of contents.
        
        Returns:
            str: A formatted table of contents string generated from the
                instance's section attributes.
        """
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
