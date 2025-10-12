import os

import tomli

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.utils import find_in_repo_tree, save_sections
from osa_tool.utils import logger, osa_project_root, parse_folder_name


class CommunityTemplateBuilder:
    """
    Builds PULL_REQUEST_TEMPLATE Markdown file.
    """

    def __init__(self, config_loader: ConfigLoader, metadata: RepositoryMetadata):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.repo_url = self.config.git.repository
        self.sourcerank = SourceRank(self.config_loader)
        self.metadata = metadata
        self.template_path = os.path.join(osa_project_root(), "docs", "templates", "community.toml")
        self.url_path = f"https://{self.config.git.host_domain}/{self.config.git.full_name}/"
        self.branch_path = f"tree/{self.metadata.default_branch}/"
        self._template = self.load_template()

        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url), "." + self.config.git.host)
        self.code_of_conduct_to_save = os.path.join(self.repo_path, "CODE_OF_CONDUCT.md")
        self.security_to_save = os.path.join(self.repo_path, "SECURITY.md")
        self._setup_paths_depends_on_platform()

    def _setup_paths_depends_on_platform(self) -> None:
        """Configures file save paths depending on the platform."""

        if "gitlab" in self.config.git.host:
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
        elif "github" in self.config.git.host:
            self.issue_templates_path = os.path.join(self.repo_path, "ISSUE_TEMPLATE")
            os.makedirs(self.issue_templates_path, exist_ok=True)
            self.pr_to_save = os.path.join(self.repo_path, "PULL_REQUEST_TEMPLATE.md")
            self.docs_issue_to_save = os.path.join(self.repo_path, "DOCUMENTATION_ISSUE.md")
            self.feature_issue_to_save = os.path.join(self.issue_templates_path, "FEATURE_ISSUE.md")
            self.bug_issue_to_save = os.path.join(self.issue_templates_path, "BUG_ISSUE.md")

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    def build_code_of_conduct(self) -> None:
        """Generates and saves the CODE_OF_CONDUCT.md file."""
        try:
            content = self._template["code_of_conduct"]
            save_sections(content, self.code_of_conduct_to_save)
            logger.info(f"CODE_OF_CONDUCT.md successfully generated in folder {self.repo_path}")
        except Exception as e:
            logger.error("Error while generating CODE_OF_CONDUCT.md: %s", repr(e), exc_info=True)

    def build_pull_request(self) -> None:
        """Generates and saves the PULL_REQUEST_TEMPLATE.md file."""
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

    def build_documentation_issue(self) -> None:
        """Generates and saves the DOCUMENTATION_ISSUE.md file if documentation is present."""
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

    def build_feature_issue(self) -> None:
        """Generates and saves the FEATURE_ISSUE.md file."""
        try:
            content = self._template["feature_issue"].format(project_name=self.metadata.name)
            save_sections(content, self.feature_issue_to_save)
            logger.info(
                f"FEATURE_ISSUE.md successfully generated in folder {os.path.dirname(self.feature_issue_to_save)}"
            )
        except Exception as e:
            logger.error("Error while generating FEATURE_ISSUE.md: %s", repr(e), exc_info=True)

    def build_bug_issue(self) -> None:
        """Generates and saves the BUG_ISSUE.md file."""
        try:
            content = self._template["bug_issue"].format(project_name=self.metadata.name)
            save_sections(content, self.bug_issue_to_save)
            logger.info(f"BUG_ISSUE.md successfully generated in folder {os.path.dirname(self.bug_issue_to_save)}")
        except Exception as e:
            logger.error("Error while generating BUG_ISSUE.md: %s", repr(e), exc_info=True)

    def build_vulnerability_disclosure(self) -> None:
        """Generates and saves the Vulnerability Disclosure.md file."""
        try:
            content = self._template["vulnerability_disclosure"]
            save_sections(content, self.vulnerability_disclosure_to_save)
            logger.info(
                f"Vulnerability Disclosure.md successfully generated in folder {os.path.dirname(self.vulnerability_disclosure_to_save)}"
            )
        except Exception as e:
            logger.error("Error while generating Vulnerability Disclosure.md: %s", repr(e), exc_info=True)

    def build_security(self) -> None:
        """Generates and saves the SECURITY.md file."""
        try:
            content = self._template[f"security_{self.config.git.host}"].format(repo_url=self.repo_url)
            save_sections(content, self.security_to_save)
            logger.info(f"SECURITY.md successfully generated in folder {self.repo_path}")
        except Exception as e:
            logger.error("Error while generating SECURITY.md: %s", repr(e), exc_info=True)
