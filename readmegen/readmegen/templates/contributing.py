import requests

from pathlib import Path
from string import Template

from readmegen.config.settings import ConfigLoader
from readmegen.ingestion.models import RepositoryContext
from readmegen.readers.git.providers import GitHost
from readmegen.readers.git.metadata import fetch_git_repository_metadata
from readmegen.utils.helpers import is_available

if is_available("tomllib"):  # pragma: no cover
    import tomllib
elif is_available("tomli"):  # pragma: no cover
    import tomli as tomllib


class ContributingBuilder:
    """
    Build the Contributing Readme section.
    """

    def __init__(
        self, config_loader: ConfigLoader, repo_context: RepositoryContext
    ):
        self.config_loader = config_loader
        self.config = config_loader.config
        self.repo_context = repo_context
        self.docs = repo_context.docs_paths
        self.md = self.config.md
        self.git = self.config.git
        self.host_domain = self.git.host_domain
        self.full_name = self.git.full_name
        self.repo_url = (
            self.git.repository
            if self.git.host_domain != GitHost.LOCAL.name.lower()
            else f"../{self.git.name}"
        )
        self.metadata = fetch_git_repository_metadata(self.repo_url)
        self.contributing_config = self._load_contributing_config()

    def _load_contributing_config(self):
        config_path = (
            Path(__file__).parent.parent
            / "config"
            / "settings"
            / "contributing_config.toml"
        )
        with open(config_path, "rb") as f:
            return tomllib.load(f)

    def _check_url(self, url):
        response = requests.get(url)
        return response.status_code == 200

    def build(self):
        main_template = Template(self.contributing_config["templates"]["main"])
        return main_template.safe_substitute(
            discussion_section=self._format_discussions(),
            issues_section=self._format_issues(),
            contributing_section=self._format_contributing(),
        )

    def _format_discussions(self) -> str:
        template = Template(
            self.contributing_config["templates"]["discussion_section"]
        )
        url = f"https://{self.host_domain}/{self.full_name}/discussions"

        if self._check_url(url=url):
            return template.safe_substitute(
                discussions_url=url,
            )
        return ""

    def _format_issues(self) -> str:
        template = Template(
            self.contributing_config["templates"]["issues_section"]
        )
        return template.safe_substitute(
            issues_url=f"https://{self.host_domain}/{self.full_name}/issues",
            repo_name=self.git.name,
        )

    def _format_contributing(self):
        template = Template(
            self.contributing_config["templates"]["contributing_section"]
        )
        base_url = f"https://{self.host_domain}/{self.full_name}/blob/"
        url = None
        for key, file in self.contributing_config["files"].items():
            for file_path in self.docs:
                if file_path.endswith(file) or file_path.endswith(
                    file.lower()
                ):
                    url = (
                        base_url
                        + f"{self.metadata.default_branch}/"
                        + f"{str(Path(file_path).as_posix())}"
                    )
                    break
            if url:
                break
        print(url)
        if self._check_url(url):
            return template.safe_substitute(
                contributing_url=url,
            )
        return ""
