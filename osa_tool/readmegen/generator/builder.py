from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.generator.base_builder import MarkdownBuilderBase
from osa_tool.readmegen.postprocessor.response_cleaner import JsonProcessor
from osa_tool.readmegen.utils import find_in_repo_tree


class MarkdownBuilder(MarkdownBuilderBase):
    """
    Builds each section of the README Markdown file.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        metadata: RepositoryMetadata,
        overview: str = None,
        core_features: str = None,
        getting_started: str = None,
    ):
        super().__init__(config_loader, metadata, overview=overview, getting_started=getting_started)
        self._core_features_json = core_features

    @property
    def core_features(self) -> str:
        """Generates the README Core Features section"""
        if not self._core_features_json:
            return ""

        features = JsonProcessor.parse(self._core_features_json, expected_type=list)
        critical = [f for f in features if isinstance(f, dict) and f.get("is_critical")]
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
