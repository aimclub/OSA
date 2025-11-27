import os

import tomli

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.utils import (
    find_in_repo_tree,
    remove_extra_blank_lines,
    save_sections,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root, parse_folder_name


class ContributingBuilder:
    """
    Builds the CONTRIBUTING.md Markdown documentation file for the project.
    """

    def __init__(self, config_loader: ConfigLoader, metadata: RepositoryMetadata):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.sourcerank = SourceRank(self.config_loader)
        self.repo_url = self.config.git.repository
        self.metadata = metadata
        self.template_path = os.path.join(osa_project_root(), "docs", "templates", "contributing.toml")
        self.url_path = f"https://{self.config.git.host_domain}/{self.config.git.full_name}/"
        self.branch_path = f"tree/{self.metadata.default_branch}/"
        self.issues_url = self.url_path + ("tasktracker" if "gitverse" in self.config.git.host else "issues")
        self._template = self.load_template()

        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url), "." + self.config.git.host)
        self.file_to_save = os.path.join(self.repo_path, "CONTRIBUTING.md")

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    @property
    def introduction(self) -> str:
        """Generates the introduction section of the contributing guidelines."""
        return self._template["introduction"].format(
            project_name=self.metadata.name,
            issues_url=self.issues_url,
        )

    @property
    def guide(self) -> str:
        """Generates the guide section with basic project contribution instructions."""
        return self._template["guide"].format(url=self.url_path, project_name=self.metadata.name)

    @property
    def before_pr(self) -> str:
        """Generates the checklist section for contributors before submitting a pull request."""
        return self._template["before_pull_request"].format(
            project_name=self.metadata.name,
            documentation=self.documentation,
            readme=self.readme,
            tests=self.tests,
        )

    @property
    def documentation(self) -> str:
        """Generates the documentation resources section link."""
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
        """Generates the README file link section."""
        if self.sourcerank.readme_presence():
            pattern = r"\bREADME(\.\w+)?\b"
            path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
        else:
            return ""
        return self._template["readme"].format(readme=path)

    @property
    def tests(self) -> str:
        """Generates the test resources section link."""
        if self.sourcerank.tests_presence():
            pattern = r"\b(tests?|testcases?|unittest|test_suite)\b"
            path = self.url_path + self.branch_path + f"{find_in_repo_tree(self.sourcerank.tree, pattern)}"
        else:
            return ""
        return self._template["tests"].format(tests=path)

    @property
    def acknowledgements(self) -> str:
        """Returns the acknowledgements section content."""
        return self._template["acknowledgements"]

    def build(self) -> None:
        """Assembles and saves the CONTRIBUTING.md file from template sections."""
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
