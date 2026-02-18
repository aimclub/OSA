import json

from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.generator.base_builder import MarkdownBuilderBase
from osa_tool.readmegen.utils import find_in_repo_tree


class MarkdownBuilder(MarkdownBuilderBase):
    """
    Builds each section of the README Markdown file.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        overview: str = None,
        core_features: str = None,
        getting_started: str = None,
    ):
        """
        Initialize the object with configuration loader and optional documentation sections.
        
        Args:
            config_loader: The configuration loader instance used to load settings.
            overview: Optional overview text for the documentation.
            core_features: Optional JSON string containing core feature information.
            getting_started: Optional getting started text for the documentation.
        
        Attributes:
            _core_features_json: Stores the core_features JSON string passed to the constructor.
        
        Returns:
            None
        """
        super().__init__(config_loader, overview=overview, getting_started=getting_started)
        self._core_features_json = core_features

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
            f"{i + 1}. **{f['feature_name']}**: {f['feature_description']}" for i, f in enumerate(critical)
        )
        return self._template["core_features"].format(formatted_features)

    @property
    def contributing(self) -> str:
        """Generates the README Contributing section"""
        discussions_url = self.url_path + "discussions"
        if self._check_url(discussions_url):
            discussions = self._template["discussion_section"].format(discussions_url=discussions_url)
        else:
            discussions = ""

        issues_url = self.url_path + "issues"
        issues = self._template["issues_section"].format(issues_url=issues_url)

        if self.sourcerank.contributing_presence():
            pattern = r"\b\w*contribut\w*\.(md|rst|txt)$"

            contributing_url = self.url_path + self.branch_path + find_in_repo_tree(self.sourcerank.tree, pattern)
            contributing = self._template["contributing_section"].format(
                contributing_url=contributing_url, name=self.config.git.name
            )
        else:
            contributing = ""

        return self._template["contributing"].format(
            dicsussion_section=discussions,
            issue_section=issues,
            contributing_section=contributing,
        )

    @property
    def toc(self) -> str:
        """
        Return a formatted table of contents string.
        
        This property builds a mapping of section titles to the corresponding
        instance attributes and passes it to `self.table_of_contents` to generate
        the final string representation. The sections included are:
        
        - Core features
        - Installation
        - Getting Started
        - Examples
        - Documentation
        - Contributing
        - License
        - Citation
        
        Args:
            self: The instance on which the property is accessed.
        
        Returns:
            str: A string representation of the table of contents.
        """
        sections = {
            "Core features": self.core_features,
            "Installation": self.installation,
            "Getting Started": self.getting_started,
            "Examples": self.examples,
            "Documentation": self.documentation,
            "Contributing": self.contributing,
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
            self.core_features,
            self.installation,
            self.getting_started,
            self.examples,
            self.documentation,
            self.contributing,
            self.license,
            self.citation,
        ]

        return "\n".join(readme_contents)
