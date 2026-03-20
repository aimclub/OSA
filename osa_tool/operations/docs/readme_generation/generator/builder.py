from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.generator.base_builder import MarkdownBuilderBase
from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree


class MarkdownBuilder(MarkdownBuilderBase):
    """
    Builds each section of the README Markdown file.
    """


    def __init__(
        self,
        config_manager: ConfigManager,
        metadata: RepositoryMetadata,
        overview: str = None,
        core_features: str = None,
        getting_started: str = None,
    ):
        """
        Initializes the repository documentation generator (MarkdownBuilder).
        
        This constructor initializes the object by setting up configuration, metadata, and documentation sections for the repository. It extends the base class constructor to handle the specific Markdown documentation generation needs.
        
        Args:
            config_manager: The configuration manager instance for accessing settings and environment variables. Provides runtime configuration for the documentation process.
            metadata: The metadata object containing repository information such as name, URL, and version. Used to populate document headers and metadata sections.
            overview: An optional high-level description of the repository. Defaults to None. If provided, it is used in the generated documentation's overview section.
            core_features: An optional JSON string detailing the core functionalities of the repository. Defaults to None. This JSON is parsed to generate a structured core features list in the final documentation.
            getting_started: An optional guide for initial setup and basic usage. Defaults to None. If provided, it is included as a "Getting Started" section in the output.
        
        Why:
            The method calls the parent constructor to handle common initialization (configuration, metadata, overview, and getting_started). It then specifically stores the `core_features` JSON string separately because the MarkdownBuilder has specialized logic to parse and format this JSON into a human-readable feature list, which is a unique requirement for Markdown output compared to other documentation formats the tool may support.
        
        Initializes the following object properties:
            _core_features_json (str or None): Stores the provided JSON string describing the repository's core features. Used for generating the core features section of the documentation. This property is specific to MarkdownBuilder.
        """
        super().__init__(config_manager, metadata, overview=overview, getting_started=getting_started)
        self._core_features_json = core_features

    @property
    def core_features(self) -> str:
        """
        Generates the README Core Features section.
        
        This property extracts and formats the critical core features from the stored JSON data. It ensures that only features marked as critical are included, providing a focused list for the README. If no critical features are identified, a placeholder message is returned.
        
        Returns:
            The formatted Core Features section as a string. Returns an empty string if no core features data is available, or a placeholder message if no critical features are found.
        """
        if not self._core_features_json:
            return ""

        critical = [f for f in self._core_features_json if isinstance(f, dict) and f.get("is_critical")]
        if not critical:
            return "_No critical features identified._"

        formatted_features = "\n".join(
            f"{i + 1}. **{f['feature_name']}**: {f['feature_description']}" for i, f in enumerate(critical)
        )
        return self._template["core_features"].format(formatted_features)

    @property
    def contributing(self) -> str:
        """
        Generates the README Contributing section.
        
        This property assembles the "Contributing" portion of a README by combining
        three optional subsections: a link to project discussions, a link to the issue
        tracker, and a link to the contribution guidelines file (if one exists in the
        repository). Each subsection is included only when its corresponding resource
        is available or valid.
        
        Why:
        - The discussions link is included only if the discussions URL is reachable,
          ensuring the README does not contain broken links.
        - The issues link is always included, as the issues URL is assumed to be a
          standard repository feature.
        - The contribution guidelines link is included only if a contributing file
          (e.g., CONTRIBUTING.md) is detected in the repository tree, promoting
          repository completeness and guiding potential contributors.
        
        Args:
            None (this is a property).
        
        Returns:
            str: The formatted "Contributing" section as a string. If subsections are
            missing, they are omitted from the final output.
        """
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
                contributing_url=contributing_url, name=self.config_manager.get_git_settings().name
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
        Generates a table of contents for the Markdown document.
        
        This property returns a formatted table of contents string by organizing
        the document's predefined sections. It utilizes the base class method
        `table_of_contents` to construct the output.
        
        The method maps each section title to its corresponding content property
        to ensure the table of contents includes only sections that have content.
        This adaptive approach allows the table of contents to be generated
        dynamically based on the actual sections present in the document.
        
        Returns:
            str: A string representing the table of contents for the Markdown document.
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
        """
        Builds the complete README.md content by concatenating all predefined sections in order.
        
        The method assembles the final README text by joining the content of each section attribute
        (header, overview, table of contents, etc.) with newline separators. This provides a consistent
        structure for the generated documentation.
        
        Returns:
            The full README.md content as a single string.
        """
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
