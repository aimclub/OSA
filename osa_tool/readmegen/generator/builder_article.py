import json
import os

import tomli

from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.generator.header import HeaderBuilder
from osa_tool.utils import osa_project_root


class MarkdownBuilderArticle:
    """
    Builds each section of the README Markdown file.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        overview: str = None,
        content: str = None,
        algorithms: str = None,
    ):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.template_path = os.path.join(
            osa_project_root(), "config", "templates", "template_article.toml"
        )

        self._overview_json = overview
        self._content_json = content
        self._algorithms_json = algorithms
        self.header_badges = HeaderBuilder(self.config_loader).build_information_section

        self._template = self.load_template()

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    @property
    def header(self):
        return self._template["headers"].format(
            project_name=self.config.git.name, info_badges=self.header_badges
        )

    @property
    def overview(self) -> str:
        """Generates the README Overview section"""
        if not self._overview_json:
            return ""
        overview_data = json.loads(self._overview_json)
        return self._template["overview"].format(overview_data["overview"])

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

    def build(self):
        """Builds each section of the README.md file."""
        readme_contents = [self.header, self.overview, self.content, self.algorithms]

        return "\n".join(readme_contents)
