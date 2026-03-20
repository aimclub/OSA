import os

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.utils import (
    find_in_repo_tree,
    remove_extra_blank_lines,
    save_sections,
)
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root, parse_folder_name


class ContributingBuilder:
    """
    Builds the CONTRIBUTING.md Markdown documentation file for the project.
    """


    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        """
        Initializes the ContributingGuideGenerator instance.
        
        Args:
            config_manager: Configuration manager providing access to settings.
            metadata: Repository metadata containing information about the repository.
        
        Initializes the following instance attributes:
            config_manager (ConfigManager): Configuration manager instance.
            sourcerank (SourceRank): SourceRank instance initialized with the config_manager.
            repo_url (str): Repository URL from git settings.
            metadata (RepositoryMetadata): Provided repository metadata.
            template_path (str): Path to the contributing guide template file, located in the project's docs/templates directory.
            url_path (str): Base URL for the repository on the hosting platform (e.g., GitHub, GitLab, Gitverse).
            branch_path (str): URL path segment for the default branch, used to construct links to files in the repository.
            issues_url (str): Full URL to the repository's issue tracker. The path segment is "tasktracker" for Gitverse hosts, otherwise "issues".
            _template (str): Loaded template content from the contributing.toml file.
            repo_path (str): Local filesystem path where the repository is located, derived from the repository URL and host name.
            file_to_save (str): Full path where the CONTRIBUTING.md file will be saved inside the repository directory.
        
        Why these attributes are set:
            The attributes are prepared to support generating a CONTRIBUTING.md file tailored to the specific repository. The URLs and paths enable creating correct links within the guide, while the template provides the structure and placeholders for repository-specific content. The repo_path and file_to_save ensure the generated file is saved in the correct local repository location.
        """
        self.config_manager = config_manager
        self.sourcerank = SourceRank(self.config_manager)
        self.repo_url = self.config_manager.get_git_settings().repository
        self.metadata = metadata
        self.template_path = os.path.join(osa_project_root(), "docs", "templates", "contributing.toml")
        self.url_path = f"https://{self.config_manager.get_git_settings().host_domain}/{self.config_manager.get_git_settings().full_name}/"
        self.branch_path = f"tree/{self.metadata.default_branch}/"
        self.issues_url = self.url_path + (
            "tasktracker" if "gitverse" in self.config_manager.get_git_settings().host else "issues"
        )
        self._template = self.load_template()

        self.repo_path = os.path.join(
            os.getcwd(), parse_folder_name(self.repo_url), "." + self.config_manager.get_git_settings().host
        )
        self.file_to_save = os.path.join(self.repo_path, "CONTRIBUTING.md")

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        
        The template is read from the path specified by `self.template_path`. This method is used to load a predefined TOML structure that serves as a base for generating or validating documentation content in the repository enhancement process.
        
        Args:
            template_path: The file system path to the TOML template file.
        
        Returns:
            A dictionary representing the parsed TOML content, where keys are section names and values are the corresponding configuration data.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    @property
    def introduction(self) -> str:
        """
        Generates the introduction section of the contributing guidelines.
        
        WHY: The introduction welcomes potential contributors by personalizing the text with the project's name and providing a direct link to the issues page, encouraging community engagement from the outset.
        
        Args:
            None: This is a property getter; it uses the instance's metadata and issues_url.
        
        Returns:
            The formatted introduction string, populated with the project name and the URL for the project's issue tracker.
        """
        return self._template["introduction"].format(
            project_name=self.metadata.name,
            issues_url=self.issues_url,
        )

    @property
    def guide(self) -> str:
        """
        Generates the guide section with basic project contribution instructions.
        
        The guide is constructed by populating a predefined template string from the builder's template data. It inserts dynamic values such as the project's URL path and its name to create context-specific contribution instructions.
        
        Args:
            url_path: The URL path for the project, used within the guide for linking or referencing the project location.
            project_name: The name of the project, used to personalize the contribution instructions.
        
        Returns:
            A formatted string containing the complete contribution guide section.
        """
        return self._template["guide"].format(url=self.url_path, project_name=self.metadata.name)

    @property
    def before_pr(self) -> str:
        """
        Generates the checklist section for contributors before submitting a pull request.
        
        This property returns a formatted string that serves as a pre-submission checklist, guiding contributors to verify key project components. It ensures that essential documentation and tests are in place, promoting consistency and quality in pull requests.
        
        Args:
            project_name: The name of the project, used for contextual labeling in the checklist.
            documentation: The status or details of the project documentation to be verified.
            readme: The status or details of the README file to be checked.
            tests: The status or details of the project tests to be validated.
        
        Returns:
            A formatted checklist string based on the provided template and parameters.
        """
        return self._template["before_pull_request"].format(
            project_name=self.metadata.name,
            documentation=self.documentation,
            readme=self.readme,
            tests=self.tests,
        )

    @property
    def documentation(self) -> str:
        """
        Generates the documentation resources section link.
        
        If the project metadata provides a homepage URL, that URL is used directly.
        Otherwise, if the repository tree indicates the presence of documentation (via keywords like 'docs', 'wiki', etc.), the method searches the tree for a matching path and constructs a URL pointing to that documentation within the repository.
        If no homepage is given and no documentation is found in the tree, an empty string is returned.
        
        Returns:
            A formatted documentation link string, or an empty string if no documentation link can be generated.
        """
        if not self.metadata.homepage_url:
            if self.sourcerank.docs_presence():
                pattern = r"\b(docs?|documentation|wiki|manuals?)\b"
                path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
            else:
                return ""
        else:
            path = self.metadata.homepage_url
        return self._template["documentation"].format(docs=path)

    @property
    def readme(self) -> str:
        """
        Generates the README file link section for the repository.
        
        If a README file is present in the repository tree, this property constructs a formatted link to it using a predefined template. If no README is found, an empty string is returned.
        
        Args:
            self: The ContributingBuilder instance.
        
        Returns:
            The formatted README link as a string, or an empty string if no README is present.
        
        Why:
            Providing a direct link to the README file enhances the generated documentation by allowing users to quickly access the main project documentation. This is part of building a comprehensive contributing guide that references key repository resources.
        """
        if self.sourcerank.readme_presence():
            pattern = r"\bREADME(\.\w+)?\b"
            path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
        else:
            return ""
        return self._template["readme"].format(readme=path)

    @property
    def tests(self) -> str:
        """
        Generates the test resources section link for the contributing guide.
        
        This property uses a regular expression to locate a test directory or file in the repository tree. If a test resource is found, it constructs a relative URL path to that resource and formats it into a predefined template link. If no test resources are detected, an empty string is returned.
        
        Why:
            The link helps users quickly navigate to the project's test suite from the contributing documentation, promoting awareness of testing practices and encouraging contributions that include tests.
        
        Args:
            None (property method).
        
        Returns:
            A formatted markdown link to the test resources section, or an empty string if no test resources are present.
        """
        if self.sourcerank.tests_presence():
            pattern = r"\b(tests?|testcases?|unittest|test_suite)\b"
            path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
        else:
            return ""
        return self._template["tests"].format(tests=path)

    @property
    def acknowledgements(self) -> str:
        """
        Returns the acknowledgements section content from the template.
        
        This property provides read-only access to the acknowledgements text stored in the internal template structure. It is used to retrieve the acknowledgements content when building or generating documentation sections.
        
        Returns:
            The acknowledgements text as defined in the template.
        """
        return self._template["acknowledgements"]

    def build(self) -> bool:
        """
        Assembles and saves the CONTRIBUTING.md file from template sections.
        
        The method combines predefined sections (introduction, guide, before_pr, acknowledgements) into a single Markdown document, ensures the target directory exists, saves the content to a file, and cleans up extra blank lines for consistent formatting.
        
        Returns:
            bool: True if the CONTRIBUTING.md file was successfully generated and saved; False if an error occurred during the process.
        """
        try:
            content = [
                self.introduction,
                self.guide,
                self.before_pr,
                self.acknowledgements,
            ]
            string_content = "\n".join(content)

            if not os.path.exists(self.repo_path):
                os.makedirs(self.repo_path)

            save_sections(string_content, self.file_to_save)
            remove_extra_blank_lines(self.file_to_save)
            logger.info(f"CONTRIBUTING.md successfully generated in folder {self.repo_path}")
        except Exception as e:
            logger.error("Error while generating CONTRIBUTING.md: %s", repr(e), exc_info=True)
            return False
        return True
