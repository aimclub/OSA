import os
import re
from functools import cached_property

import requests
import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.generator.header import HeaderBuilder
from osa_tool.operations.docs.readme_generation.generator.installation import InstallationSectionBuilder
from osa_tool.operations.docs.readme_generation.models.llm_service import LLMClient
from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.utils import osa_project_root


class MarkdownBuilderBase:
    """
    Base class for building Markdown content, specifically designed for generating README files.
    
        This class provides a foundation for constructing various sections of a README document,
        such as overview, installation instructions, and examples. It handles configuration
        management, template loading, and URL validation to support the content generation process.
    
        Attributes:
            config_manager (ConfigManager): Manages configuration settings and provides access to prompts and git settings.
            sourcerank (SourceRank): SourceRank calculator for repository analysis.
            prompts (PromptLoader): Loader for prompt templates used in content generation.
            repo_url (str): URL of the git repository.
            metadata (RepositoryMetadata): Repository metadata including default branch.
            url_path (str): Base URL path to the repository on the hosting platform.
            branch_path (str): URL path segment for the default branch.
            _overview (any): Optional pre-built overview section content.
            _getting_started (any): Optional pre-built getting started section content.
            header (str): Formatted header section combining project name and badges.
            installation (str): Formatted installation instructions section.
            template_path (str): File system path to the template configuration file.
            _template (str): Loaded content of the template configuration file.
    
        Methods:
            __init__: Initializes the README generator with configuration, metadata, and optional content sections.
            load_template: Loads a TOML template file and returns its sections as a dictionary.
            _check_url: Verifies if a given URL is accessible and returns a successful status code.
            overview: Generates the README Overview section.
            getting_started: Generates the README Getting Started section.
            examples: Generates the README Examples section.
            documentation: Generates the README Documentation section.
            license: Generates the README License section.
            citation: Generates the README Citation section.
            table_of_contents: Generates an adaptive Table of Contents based on provided sections.
    """

    def __init__(
        self,
        config_manager: ConfigManager,
        metadata: RepositoryMetadata,
        overview=None,
        getting_started=None,
    ):
        """
        Initializes the README generator with configuration, metadata, and optional content sections.
        
        Args:
            config_manager: Manages configuration settings and provides access to prompts and git settings.
            metadata: Contains repository metadata including default branch information.
            overview: Optional pre-built overview section content. If provided, it is stored for later use in the README.
            getting_started: Optional pre-built getting started section content. If provided, it is stored for later use in the README.
        
        Initializes the following instance attributes:
            config_manager (ConfigManager): Configuration manager for accessing settings and prompts.
            sourcerank (SourceRank): SourceRank calculator for repository analysis, instantiated using the config_manager.
            prompts (PromptLoader): Loader for prompt templates used in content generation, retrieved from the config_manager.
            repo_url (str): URL of the git repository, derived from the git settings in the config_manager.
            metadata (RepositoryMetadata): Repository metadata including default branch.
            url_path (str): Base URL path to the repository on the hosting platform, constructed from git settings.
            branch_path (str): URL path segment for the default branch, used for linking to files within the repository.
            _overview (any): Optional pre-built overview section content.
            _getting_started (any): Optional pre-built getting started section content.
            header (str): Formatted header section combining project name and badges, built by HeaderBuilder.
            installation (str): Formatted installation instructions section, built by InstallationSectionBuilder.
            template_path (str): File system path to the template configuration file, located in the project's config/templates directory.
            _template (str): Loaded content of the template configuration file, populated by calling load_template().
        
        The constructor sets up core components needed for README generation, including URL paths for repository links and pre-built sections for header and installation. The optional overview and getting_started parameters allow for pre-generated content to be supplied, avoiding redundant generation if already available.
        """
        self.config_manager = config_manager
        self.sourcerank = SourceRank(self.config_manager)
        self.prompts = self.config_manager.get_prompts()
        self.repo_url = self.config_manager.get_git_settings().repository
        self.metadata = metadata
        self.url_path = f"https://{self.config_manager.get_git_settings().host_domain}/{self.config_manager.get_git_settings().full_name}/"
        self.branch_path = f"tree/{self.metadata.default_branch}/"

        self._overview = overview
        self._getting_started = getting_started

        self.header = HeaderBuilder(self.config_manager, self.metadata).build_header()
        self.installation = InstallationSectionBuilder(self.config_manager, self.metadata).build_installation()

        self.template_path = os.path.join(osa_project_root(), "config", "templates", "template.toml")
        self._template = self.load_template()

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        
        The template file is read from the path specified by `self.template_path`.
        The method uses the `tomli` library to parse the TOML content and return it as a structured dictionary, preserving the sections and key-value pairs defined in the template file.
        
        Args:
            template_path: The file path to the TOML template to be loaded.
        
        Returns:
            A dictionary representing the parsed TOML content from the template file.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    @staticmethod
    def _check_url(url):
        """
        Verifies if a given URL is accessible and returns a successful status code.
        
        This is a static helper method used to validate external links, typically during documentation generation or content validation, ensuring that referenced URLs are reachable.
        
        Args:
            url: The URL string to be checked.
        
        Returns:
            bool: True if the HTTP request to the URL returns a status code of 200, False otherwise.
        """
        response = requests.get(url)
        return response.status_code == 200

    @property
    def overview(self) -> str:
        """
        Generates the README Overview section.
        
        This property returns a formatted string for the Overview section of the README,
        using a predefined template. If no overview content is provided (i.e., `self._overview`
        is empty or falsy), an empty string is returned to avoid unnecessary sections.
        
        Args:
            None (this is a property, so no explicit parameters are taken).
        
        Returns:
            The formatted Overview section as a string, or an empty string if no overview content exists.
        """
        if not self._overview:
            return ""
        return self._template["overview"].format(self._overview)

    @property
    def getting_started(self) -> str:
        """
        Generates the README Getting Started section.
        
        This property returns a formatted string for the "Getting Started" section of the README,
        using a predefined template. If no getting started content is provided (i.e., `self._getting_started` is empty or falsy),
        an empty string is returned to omit the section entirely.
        
        Why: This allows the README to dynamically include or exclude the Getting Started section
        based on whether content has been supplied, avoiding empty or placeholder sections in the final output.
        
        Returns:
            The formatted Getting Started section as a string, or an empty string if no content is available.
        """
        if not self._getting_started:
            return ""
        return self._template["getting_started"].format(self._getting_started)

    @property
    def examples(self) -> str:
        """
        Generates the README Examples section.
        
        This property returns a formatted string for the Examples section if the repository contains example-related files (tutorials, examples, or notebooks). If no such files are found, it returns an empty string.
        
        Why:
        - The method checks for the presence of example files to determine whether to include an Examples section in the README, avoiding empty sections.
        - It constructs a URL path to the located examples directory or file, making it easy for users to navigate to the examples directly from the README.
        
        Returns:
            str: A formatted Examples section string with a link to the examples location, or an empty string if no examples are present.
        """
        if not self.sourcerank.examples_presence():
            return ""

        pattern = r"\b(tutorials?|examples|notebooks?)\b"
        path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
        return self._template["examples"].format(path=path)

    @property
    def documentation(self) -> str:
        """
        Generates the README Documentation section.
        
        This property determines the appropriate documentation link to include in the README.
        If the repository metadata specifies a homepage URL, that URL is used.
        Otherwise, if the repository tree contains documentation-related files or directories (e.g., 'docs', 'wiki'), the method constructs a path to the first matching item within the repository.
        If no homepage URL is provided and no documentation is found in the tree, an empty string is returned.
        
        Why:
            Providing a direct link to documentation improves project accessibility.
            When a dedicated homepage is not specified, the method attempts to locate existing documentation within the repository itself to ensure users can still find relevant documentation links.
        
        Returns:
            str: The formatted documentation section string for the README, or an empty string if no documentation source is available.
        """
        if not self.metadata.homepage_url:
            if self.sourcerank.docs_presence():
                pattern = r"\b(docs?|documentation|wiki|manuals?)\b"
                path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
            else:
                return ""
        else:
            path = self.metadata.homepage_url
        return self._template["documentation"].format(repo_name=self.metadata.name, path=path)

    @property
    def license(self) -> str:
        """
        Generates the README License section.
        
        If a license name is not available in the metadata, returns an empty string.
        Otherwise, attempts to locate a license file in the repository tree by searching for a pattern matching "LICENSE" or "LICENCE" (case-insensitive, with optional extension). If found, constructs a URL path to that file; otherwise, falls back to the license URL from the metadata. The result is formatted using a predefined template.
        
        Returns:
            str: The formatted license section for the README, or an empty string if no license is present.
        """
        if not self.metadata.license_name:
            return ""

        pattern = r"\bLICEN[SC]E(\.\w+)?\b"
        help_var = find_in_repo_tree(self.sourcerank.tree, pattern)
        path = self.url_path + self.branch_path + help_var if help_var else self.metadata.license_url
        return self._template["license"].format(license_name=self.metadata.license_name, path=path)

    @cached_property
    def citation(self) -> str:
        """
        Generates the README Citation section.
        
        The method attempts to produce a citation entry for the repository. It first checks if a dedicated citation file (e.g., CITATION, CITATION.md) exists in the repository tree. If found, it creates a link to that file. Otherwise, it uses an LLM to extract a citation from the existing README content. If that also fails, it falls back to generating a default citation using repository metadata.
        
        Why:
        - Providing a proper citation is important for academic attribution and giving credit in open‑source projects.
        - The method prioritizes existing citation files, then LLM-extracted content, and finally a generated template to ensure a citation is always available.
        
        Args:
            self: The instance of MarkdownBuilderBase.
        
        Returns:
            str: The complete citation section formatted as a markdown string.
        """
        if self.sourcerank.citation_presence():
            pattern = r"\bCITATION(\.\w+)?\b"
            path = self.url_path + self.branch_path + find_in_repo_tree(self.sourcerank.tree, pattern)
            return self._template["citation"] + self._template["citation_v1"].format(path=path)

        llm_client = LLMClient(self.config_manager, self.metadata)
        citation_from_readme = llm_client.get_citation_from_readme()

        if citation_from_readme:
            return self._template["citation"] + citation_from_readme

        return self._template["citation"] + self._template["citation_v2"].format(
            owner=self.metadata.owner,
            year=self.metadata.created_at.split("-")[0],
            repo_name=self.config_manager.get_git_settings().name,
            publisher=self.config_manager.get_git_settings().host_domain,
            repository_url=self.config_manager.get_git_settings().repository,
        )

    @staticmethod
    def table_of_contents(sections: dict) -> str:
        """
        Generates an adaptive Table of Contents (ToC) in Markdown format based on provided sections.
        
        The method creates a ToC that links to each non-empty section within the same document. This is used to improve document navigation and accessibility, especially in generated READMEs or reports.
        
        Args:
            sections: A dictionary where each key is a section name and each value is the content of that section. Only sections with non-empty content are included in the ToC.
        
        Returns:
            A string containing the complete Markdown-formatted Table of Contents, including a header, a list of clickable section links, and a horizontal rule separator at the end.
        """
        toc = ["## Table of Contents\n"]

        for section_name, section_content in sections.items():
            if section_content:
                toc.append("- [{}]({})".format(section_name, "#" + re.sub(r"\s+", "-", section_name.lower())))

        toc.append("\n---")
        return "\n".join(toc)
