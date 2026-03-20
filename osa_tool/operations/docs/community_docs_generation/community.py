import os

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree, save_sections
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root, parse_folder_name


class CommunityTemplateBuilder:
    """
    Builds PULL_REQUEST_TEMPLATE Markdown file.
    """


    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        """
        Initializes a CommunityTemplateBuilder instance.
        
        Sets up paths and loads necessary components for generating community
        documentation files based on repository configuration and metadata.
        
        Args:
            config_manager: Manages configuration settings including Git repository details.
            metadata: Contains repository metadata such as default branch.
        
        Class fields initialized:
            config_manager (ConfigManager): Manages configuration settings.
            repo_url (str): URL of the Git repository, derived from config_manager.
            sourcerank (SourceRank): SourceRank instance for repository analysis.
            metadata (RepositoryMetadata): Repository metadata.
            template_path (str): Path to the community.toml template file, located in the project's docs/templates directory.
            url_path (str): Base URL for the repository (e.g., "https://host/owner/repo/").
            branch_path (str): URL path segment for the default branch (e.g., "tree/main/").
            _template (str): Loaded template content from community.toml.
            repo_path (str): Local filesystem path for repository files, constructed by parsing the repo URL and appending a host-specific subdirectory.
            code_of_conduct_to_save (str): Path where CODE_OF_CONDUCT.md will be saved inside repo_path.
            security_to_save (str): Path where SECURITY.md will be saved inside repo_path.
        
        After initialization, the method calls `_setup_paths_depends_on_platform` to configure platform-specific template directories (e.g., for GitHub or GitLab issue and pull/merge request templates). This ensures the correct file structure is prepared for the repository's hosting platform.
        """
        self.config_manager = config_manager
        self.repo_url = self.config_manager.get_git_settings().repository
        self.sourcerank = SourceRank(self.config_manager)
        self.metadata = metadata
        self.template_path = os.path.join(osa_project_root(), "docs", "templates", "community.toml")
        self.url_path = f"https://{self.config_manager.get_git_settings().host_domain}/{self.config_manager.get_git_settings().full_name}/"
        self.branch_path = f"tree/{self.metadata.default_branch}/"
        self._template = self.load_template()

        self.repo_path = os.path.join(
            os.getcwd(), parse_folder_name(self.repo_url), "." + self.config_manager.get_git_settings().host
        )
        self.code_of_conduct_to_save = os.path.join(self.repo_path, "CODE_OF_CONDUCT.md")
        self.security_to_save = os.path.join(self.repo_path, "SECURITY.md")
        self._setup_paths_depends_on_platform()

    def _setup_paths_depends_on_platform(self) -> None:
        """
        Configures file save paths for issue and pull/merge request templates based on the detected Git platform.
        
        This method sets instance attributes for template directory paths and full file paths according to whether the repository host is GitLab or GitHub. It ensures the necessary directories exist by creating them if needed. This platform-specific setup is required because GitLab and GitHub use different default locations and naming conventions for their issue and merge/pull request templates.
        
        Args:
            None: This method uses instance attributes (self.config_manager, self.repo_path) and does not accept external parameters.
        
        The behavior is as follows:
        - If the Git host contains "gitlab":
            - Creates `issue_templates` and `merge_request_templates` directories inside the repository root.
            - Sets paths for a merge request template and several issue templates (documentation, feature, bug, vulnerability disclosure) within those directories.
        - If the Git host contains "github":
            - Creates an `ISSUE_TEMPLATE` directory inside the repository root.
            - Sets the pull request template path directly in the repository root.
            - Sets paths for issue templates (documentation, feature, bug) inside the `ISSUE_TEMPLATE` directory.
        
        No value is returned.
        """

        if "gitlab" in self.config_manager.get_git_settings().host:
            self.issue_templates_path = os.path.join(self.repo_path, "issue_templates")
            self.merge_request_templates_path = os.path.join(self.repo_path, "merge_request_templates")
            os.makedirs(self.issue_templates_path, exist_ok=True)
            os.makedirs(self.merge_request_templates_path, exist_ok=True)

            self.pr_to_save = os.path.join(self.merge_request_templates_path, "MERGE_REQUEST_TEMPLATE.md")
            self.docs_issue_to_save = os.path.join(self.issue_templates_path, "DOCUMENTATION_ISSUE.md")
            self.feature_issue_to_save = os.path.join(self.issue_templates_path, "FEATURE_ISSUE.md")
            self.bug_issue_to_save = os.path.join(self.issue_templates_path, "BUG_ISSUE.md")
            self.vulnerability_disclosure_to_save = os.path.join(
                self.issue_templates_path, "Vulnerability_Disclosure.md"
            )
        elif "github" in self.config_manager.get_git_settings().host:
            self.issue_templates_path = os.path.join(self.repo_path, "ISSUE_TEMPLATE")
            os.makedirs(self.issue_templates_path, exist_ok=True)
            self.pr_to_save = os.path.join(self.repo_path, "PULL_REQUEST_TEMPLATE.md")
            self.docs_issue_to_save = os.path.join(self.repo_path, "DOCUMENTATION_ISSUE.md")
            self.feature_issue_to_save = os.path.join(self.issue_templates_path, "FEATURE_ISSUE.md")
            self.bug_issue_to_save = os.path.join(self.issue_templates_path, "BUG_ISSUE.md")

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        
        Args:
            template_path: The file path to the TOML template to be loaded.
        
        Returns:
            A dictionary containing the parsed sections from the TOML template file.
        
        Why:
            This method reads a TOML file from the instance's template_path to provide a structured dictionary of its contents. It is used to access template data for further processing or configuration within the CommunityTemplateBuilder.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    def build_code_of_conduct(self) -> bool:
        """
        Generates and saves the CODE_OF_CONDUCT.md file.
        
        The method retrieves the code of conduct template content from the builder's configuration,
        then writes it to a file in the repository directory. This is part of automating community
        documentation to ensure consistent and accessible project standards.
        
        Returns:
            True if the file was generated and saved successfully; False if any error occurred.
        """
        try:
            content = self._template["code_of_conduct"]
            save_sections(content, self.code_of_conduct_to_save)
            logger.info(f"CODE_OF_CONDUCT.md successfully generated in folder {self.repo_path}")
        except Exception as e:
            logger.error("Error while generating CODE_OF_CONDUCT.md: %s", repr(e), exc_info=True)
            return False
        return True

    def build_pull_request(self) -> bool:
        """
        Generates and saves the PULL_REQUEST_TEMPLATE.md file.
        
        The method creates a pull request template by formatting a predefined template with a link to the project's contribution guidelines. If contribution guidelines are found in the repository, their URL is included; otherwise, a placeholder text is used. This ensures that contributors are directed to proper contribution instructions when submitting pull requests.
        
        Args:
            self: The instance of the CommunityTemplateBuilder class.
        
        Returns:
            bool: True if the template was successfully generated and saved, False if an error occurred during the process.
        """
        try:
            if self.sourcerank.contributing_presence():
                pattern = r"\b\w*contribut\w*\.(md|rst|txt)$"
                contributing_url = self.url_path + self.branch_path + find_in_repo_tree(self.sourcerank.tree, pattern)
            else:
                contributing_url = "Provide the link"

            content = self._template["pull_request"].format(contributing_url=contributing_url)
            save_sections(content, self.pr_to_save)
            logger.info(f"PULL_REQUEST_TEMPLATE.md successfully generated in folder {os.path.dirname(self.pr_to_save)}")
        except Exception as e:
            logger.error(
                "Error while generating PULL_REQUEST_TEMPLATE.md: %s",
                repr(e),
                exc_info=True,
            )
            return False
        return True

    def build_documentation_issue(self) -> bool:
        """
        Generates and saves the DOCUMENTATION_ISSUE.md file if documentation is present in the repository.
        
        Why:
        This method ensures that a documentation issue template is created only when the repository contains documentation-related files or directories. This prevents generating unnecessary files for projects without documentation and focuses enhancement efforts where they are relevant.
        
        The method checks for documentation presence using the SourceRank utility. If documentation is detected, it retrieves a predefined documentation issue template from the builder's template configuration, saves it as a Markdown file, and logs the success. If any error occurs during the process, the error is logged and the method indicates failure.
        
        Args:
            self: The instance of the CommunityTemplateBuilder.
        
        Returns:
            True if the file was successfully generated and saved, or if no documentation was present (considered a successful non-action). Returns False if an error occurred during the generation or saving process.
        """
        try:
            if self.sourcerank.docs_presence():
                content = self._template["docs_issue"]
                save_sections(content, self.docs_issue_to_save)
                logger.info(
                    f"DOCUMENTATION_ISSUE.md successfully generated in folder {os.path.dirname(self.docs_issue_to_save)}"
                )
        except Exception as e:
            logger.error(
                "Error while generating DOCUMENTATION_ISSUE.md: %s",
                repr(e),
                exc_info=True,
            )
            return False
        return True

    def build_feature_issue(self) -> bool:
        """
        Generates and saves the FEATURE_ISSUE.md file.
        
        This method populates a predefined template with project-specific details (specifically the project name) to create a standardized feature request or issue tracking document for the community. The resulting Markdown file is saved to a predetermined location.
        
        Args:
            None. Uses instance attributes: `self._template["feature_issue"]` for the template, `self.metadata.name` for the project name, and `self.feature_issue_to_save` for the output file path.
        
        Returns:
            True if the file was generated and saved successfully. Returns False if any error occurs during template formatting or file writing, and logs the error.
        """
        try:
            content = self._template["feature_issue"].format(project_name=self.metadata.name)
            save_sections(content, self.feature_issue_to_save)
            logger.info(
                f"FEATURE_ISSUE.md successfully generated in folder {os.path.dirname(self.feature_issue_to_save)}"
            )
        except Exception as e:
            logger.error("Error while generating FEATURE_ISSUE.md: %s", repr(e), exc_info=True)
            return False
        return True

    def build_bug_issue(self) -> bool:
        """
        Generates and saves the BUG_ISSUE.md file.
        
        The method formats a predefined bug issue template using the project's name,
        then writes the resulting content to a specified Markdown file.
        
        Returns:
            True if the file was generated and saved successfully, False if any error occurred.
        """
        try:
            content = self._template["bug_issue"].format(project_name=self.metadata.name)
            save_sections(content, self.bug_issue_to_save)
            logger.info(f"BUG_ISSUE.md successfully generated in folder {os.path.dirname(self.bug_issue_to_save)}")
        except Exception as e:
            logger.error("Error while generating BUG_ISSUE.md: %s", repr(e), exc_info=True)
            return False
        return True

    def build_vulnerability_disclosure(self) -> bool:
        """
        Generates and saves the Vulnerability Disclosure.md file.
        
        The method retrieves the vulnerability disclosure template content from the builder's template data,
        then writes it to a specified file path using a helper function. This file is part of the standard
        community documentation that outlines the project's policy for reporting and handling security vulnerabilities.
        
        Returns:
            True if the file was generated and saved successfully; False if any error occurred during the process.
        """
        try:
            content = self._template["vulnerability_disclosure"]
            save_sections(content, self.vulnerability_disclosure_to_save)
            logger.info(
                f"Vulnerability Disclosure.md successfully generated in folder {os.path.dirname(self.vulnerability_disclosure_to_save)}"
            )
        except Exception as e:
            logger.error("Error while generating Vulnerability Disclosure.md: %s", repr(e), exc_info=True)
            return False
        return True

    def build_security(self) -> bool:
        """
        Generates and saves the SECURITY.md file for the repository.
        
        The method selects a security template based on the Git hosting platform (e.g., GitHub, GitLab) configured in the project settings, formats it with the repository URL, and writes the content to the specified file path.
        
        Args:
            None. Uses instance attributes:
                - self._template: A dictionary containing security templates keyed by host platform.
                - self.config_manager: Provides Git settings to determine the hosting platform.
                - self.repo_url: The repository URL used to personalize the template.
                - self.security_to_save: The file path where SECURITY.md will be saved.
                - self.repo_path: The repository root path, used for logging.
        
        Returns:
            True if the file was generated and saved successfully, False if any error occurred during the process.
        """
        try:
            content = self._template[f"security_{self.config_manager.get_git_settings().host}"].format(
                repo_url=self.repo_url
            )
            save_sections(content, self.security_to_save)
            logger.info(f"SECURITY.md successfully generated in folder {self.repo_path}")
        except Exception as e:
            logger.error("Error while generating SECURITY.md: %s", repr(e), exc_info=True)
            return False
        return True
