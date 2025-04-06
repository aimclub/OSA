import json
import os

import tomli

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.utils import find_in_repo_tree
from osa_tool.utils import osa_project_root


class MarkdownBuilder:
    """
    Builds each section of the README Markdown file.
    """

    def __init__(self,
                 config_loader: ConfigLoader,
                 overview: str = None,
                 core_features: str = None
                 ):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.sourcerank = SourceRank(self.config_loader)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.template_path = os.path.join(
            osa_project_root(),
            "config",
            "templates",
            "template.toml"
        )
        self.url_path = (
            f"https://{self.config.git.host_domain}/"
            f"{self.config.git.full_name}/tree/"
            f"{self.metadata.default_branch}/"
        )
        self._overview_json = overview
        self._core_features_json = core_features
        self._template = self.load_template()

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    @property
    def overview(self) -> str:
        """Generates the README Overview section"""
        if not self._overview_json:
            return ""
        overview_data = json.loads(self._overview_json)
        return self._template["overview"].format(overview_data["overview"])

    @property
    def core_features(self) -> str:
        """Generates the README Core Features section"""
        if not self._core_features_json:
            return ""

        features = json.loads(self._core_features_json)
        critical = [f for f in features if f.get("is_critical") is True]
        if not critical:
            return "_No critical features identified._"

        formatted_features = "\n".join(
            f"{i + 1}. **{f['feature_name']}**: {f['feature_description']}"
            for i, f in enumerate(critical)
        )
        return self._template["core_features"].format(formatted_features)

    @property
    def examples(self) -> str:
        """Generates the README Examples section"""
        pattern = r'\b(tutorials?|examples|notebooks?)\b'
        if not self.sourcerank.examples_presence():
            return ""

        path = self.url_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
        return self._template["examples"].format(path=path)

    @property
    def documentation(self) -> str:
        """Generates the README Documentation section"""
        pattern = r'\b(docs?|documentation|wiki|manuals?)\b'
        if not self.metadata.homepage_url:
            if self.sourcerank.docs_presence():
                path = self.url_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
            else:
                return ""
        else:
            path = self.metadata.homepage_url
        return self._template["documentation"].format(repo_name=self.metadata.name, path=path)

    @property
    def license(self) -> str:
        """Generates the README License section"""
        pattern = r'\bLICEN[SC]E(\.\w+)?\b'
        if not self.metadata.license_name:
            return ""

        help_var = find_in_repo_tree(self.sourcerank.tree, pattern)
        path = self.url_path + help_var if help_var else self.metadata.license_url
        return self._template["license"].format(license_name=self.metadata.license_name, path=path)

    @property
    def citation(self) -> str:
        """Generates the README Citation section"""
        pattern = r'\bCITATION(\.\w+)?\b'
        if self.sourcerank.citation_presence():
            path = self.url_path + find_in_repo_tree(self.sourcerank.tree, pattern)
            return self._template["citation"] + self._template["citation_v1"].format(path=path)

        return self._template["citation"] + self._template["citation_v2"].format(
            owner=self.metadata.owner,
            year=self.metadata.created_at.split('-')[0],
            repo_name=self.config.git.name,
            publisher=self.config.git.host_domain,
            repository_url=self.config.git.repository,
        )

    def build(self) -> str:
        """Builds each section of the README.md file."""
        readme_contents = [
            self.overview,
            self.core_features,
            self.examples,
            self.documentation,
            self.license,
            self.citation
        ]

        return "\n".join(readme_contents)
