import os

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.readme_utils import (
    find_in_repo_tree,
    remove_extra_blank_lines,
    save_sections,
)
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import build_repo_browse_url, osa_project_root, resolve_repo_path, resolve_repo_web_identity


class ContributingBuilder:
    """
    Builds the CONTRIBUTING.md Markdown documentation file for the project.
    """

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        self.config_manager = config_manager
        self.sourcerank = SourceRank(self.config_manager)
        self.repo_url = self.config_manager.get_git_settings().repository
        self.metadata = metadata
        self.template_path = os.path.join(osa_project_root(), "docs", "templates", "contributing.toml")
        git = self.config_manager.get_git_settings()
        self.host, self.host_domain, self.full_name = resolve_repo_web_identity(
            repo_url=self.repo_url,
            clone_url_http=self.metadata.clone_url_http,
            host=git.host,
            host_domain=git.host_domain,
            full_name=git.full_name,
        )
        self.host = self.host or "github"
        self.url_path = build_repo_browse_url(
            repo_url=self.repo_url,
            default_branch=self.metadata.default_branch,
            host=self.host,
            host_domain=self.host_domain,
            full_name=self.full_name,
            clone_url_http=self.metadata.clone_url_http,
        )
        self.issues_url = self.metadata.issues_url or (
            f"{self.url_path}{'tasktracker' if 'gitverse' in self.host else 'issues'}"
            if self.url_path != "."
            else "."
        )
        self._template = self.load_template()
        repo_root = resolve_repo_path(self.repo_url)
        if "sourcecraft" in self.host:
            self.repo_path = str(repo_root)
        else:
            self.repo_path = str(repo_root / f".{self.host}")
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
        return self._template["guide"].format(
            url=self.url_path if self.url_path != "." else "./",
            project_name=self.metadata.name,
            clone_url=self.metadata.clone_url_http or self.url_path,
        )

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
                path = build_repo_browse_url(
                    repo_url=self.repo_url,
                    default_branch=self.metadata.default_branch,
                    relative_path=find_in_repo_tree(self.sourcerank.tree, pattern),
                    host=self.host,
                    host_domain=self.host_domain,
                    full_name=self.full_name,
                    clone_url_http=self.metadata.clone_url_http,
                )
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
            path = build_repo_browse_url(
                repo_url=self.repo_url,
                default_branch=self.metadata.default_branch,
                relative_path=find_in_repo_tree(self.sourcerank.tree, pattern),
                host=self.host,
                host_domain=self.host_domain,
                full_name=self.full_name,
                clone_url_http=self.metadata.clone_url_http,
            )
        else:
            return ""
        return self._template["readme"].format(readme=path)

    @property
    def tests(self) -> str:
        """Generates the test resources section link."""
        if self.sourcerank.tests_presence():
            pattern = r"\b(tests?|testcases?|unittest|test_suite)\b"
            path = build_repo_browse_url(
                repo_url=self.repo_url,
                default_branch=self.metadata.default_branch,
                relative_path=find_in_repo_tree(self.sourcerank.tree, pattern),
                host=self.host,
                host_domain=self.host_domain,
                full_name=self.full_name,
                clone_url_http=self.metadata.clone_url_http,
            )
        else:
            return ""
        return self._template["tests"].format(tests=path)

    @property
    def acknowledgements(self) -> str:
        """Returns the acknowledgements section content."""
        return self._template["acknowledgements"]

    def build(self) -> bool:
        """
        Assembles and saves the CONTRIBUTING.md file from template sections.
        Returns:
            Has the task been completed successfully
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
