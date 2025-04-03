import enum
import logging
import os
import functools
from dataclasses import dataclass
from functools import lru_cache
from pydantic import (
    BaseModel,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)
import requests
from rich.logging import RichHandler
from pathlib import Path
from osa_tool.utils import get_base_repo_url
from osa_tool.readmeai.errors import GitURLError

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

logger = logging.getLogger("rich")


@dataclass
class RepositoryMetadata:
    """
    Dataclass to store GitHub repository metadata.
    """
    name: str
    full_name: str
    owner: str
    owner_url: str | None
    description: str | None

    # Repository statistics
    stars_count: int
    forks_count: int
    watchers_count: int
    open_issues_count: int

    # Repository details
    default_branch: str
    created_at: str
    updated_at: str
    pushed_at: str
    size_kb: int

    # Repository URLs
    clone_url_http: str
    clone_url_ssh: str
    contributors_url: str | None
    languages_url: str
    issues_url: str | None

    # Programming languages and topics
    language: str | None
    languages: list[str]
    topics: list[str]

    # Additional repository settings
    has_wiki: bool
    has_issues: bool
    has_projects: bool
    is_private: bool
    homepage_url: str | None

    # License information
    license_name: str | None
    license_url: str | None


def _parse_repository_metadata(repo_data: dict) -> RepositoryMetadata:
    """
    Converts raw repository data from GitHub API into dataclass.
    """
    languages = repo_data.get("languages", {})
    license_info = repo_data.get("license", {}) or {}
    owner_info = repo_data.get("owner", {}) or {}

    return RepositoryMetadata(
        name=repo_data.get("name", ""),
        full_name=repo_data.get("full_name", ""),
        owner=owner_info.get("login", ""),
        owner_url=owner_info.get("html_url", ""),
        description=repo_data.get("description", ""),
        stars_count=repo_data.get("stargazers_count", 0),
        forks_count=repo_data.get("forks_count", 0),
        watchers_count=repo_data.get("watchers_count", 0),
        open_issues_count=repo_data.get("open_issues_count", 0),
        default_branch=repo_data.get("default_branch", ""),
        created_at=repo_data.get("created_at", ""),
        updated_at=repo_data.get("updated_at", ""),
        pushed_at=repo_data.get("pushed_at", ""),
        size_kb=repo_data.get("size", 0),
        clone_url_http=repo_data.get("clone_url", ""),
        clone_url_ssh=repo_data.get("ssh_url", ""),
        contributors_url=repo_data.get("contributors_url"),
        languages_url=repo_data.get("languages_url", ""),
        issues_url=repo_data.get("issues_url"),
        language=repo_data.get("language", ""),
        languages=list(languages.keys()) if languages else [],
        topics=repo_data.get("topics", []),
        has_wiki=repo_data.get("has_wiki", False),
        has_issues=repo_data.get("has_issues", False),
        has_projects=repo_data.get("has_projects", False),
        is_private=repo_data.get("private", False),
        homepage_url=repo_data.get("homepage", ""),
        license_name=license_info.get("name", ""),
        license_url=license_info.get("url", ""),
    )


@lru_cache(maxsize=1)
def load_data_metadata(repo_url: str) -> RepositoryMetadata | None:
    """
    Retrieves GitHub repository metadata and returns a dataclass.
    """
    try:
        headers = {
            "Authorization": f"token {os.getenv('GIT_TOKEN')}",
            "Accept": "application/vnd.github.v3+json"
        }
        base_url = get_base_repo_url(repo_url)
        url = f"https://api.github.com/repos/{base_url}"

        response = requests.get(url=url, headers=headers)

        metadata = response.json()
        logger.info(f"Successfully fetched metadata for repository: {repo_url}")
        return _parse_repository_metadata(metadata)
    except requests.RequestException as exc:
        logger.error(f"Error while fetching repository metadata: {exc}")


class GitHost(enum.Enum):
    """
    Git repository hosting providers.
    """

    GITHUB = (
        "github.com",
        "https://api.github.com/repos/",
        "https://github.com/{full_name}/blob/main/{file_path}",
    )

    def __init__(self, name: str, api_url: str, file_url_template: str):
        self.domain = name
        self.api_url = api_url
        self.file_url_template = file_url_template


class GitURL(BaseModel):
    """
    Git repository URL model with validation and parsing methods.
    """

    url: HttpUrl
    host: GitHost | None = Field(default=None)
    host_domain: str = Field(default="")
    name: str = Field(default="")
    full_name: str = Field(default="")

    model_config = {
        "frozen": True,
        "use_enum_values": True,
        "extra": "forbid",
        "arbitrary_types_allowed": True,
    }

    @classmethod
    @functools.lru_cache(maxsize=100)
    def create(cls, url: HttpUrl) -> "GitURL":
        """Create a GitURL object from a string URL."""
        return cls(url=url)

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        """Validates the Git repository URL."""
        try:
            parse_git_url(str(v))
        except ValueError as e:
            raise ValueError(f"Invalid Git repository URL: {v}") from e
        return v

    @model_validator(mode="after")
    def set_attributes(self) -> "GitURL":
        """Sets the Git URL attributes based on the URL."""
        try:
            host_domain, host, name, full_name = parse_git_url(str(self.url))
            object.__setattr__(self, "host_domain", host_domain)
            object.__setattr__(self, "name", name)
            object.__setattr__(self, "full_name", full_name)
            for git_host in GitHost:
                if git_host.name.lower() == host:
                    object.__setattr__(self, "host", git_host)
                    break
        except ValueError as e:
            raise ValueError(f"Failed to parse Git URL: {self.url}") from e
        return self

    def get_api_url(self) -> str:
        """Return the REST API endpoint URL for a git repository."""
        if self.host is None:
            raise ValueError(
                f"Unsupported Git host or local repository: {self.url}",
            )
        if self.full_name:
            return f"{self.host.api_url}{self.full_name}"
        else:
            raise ValueError("Repository full name is required.")

    def get_file_url(self, file_path: str) -> str:
        """Return the URL of the file in the remote repository."""
        if self.host:
            return self.host.file_url_template.format(
                full_name=self.full_name,
                file_path=file_path,
            )
        raise ValueError(f"Unsupported Git host: {self.url}")


def parse_git_url(url: str | Path) -> tuple[str, str, str, str]:
    """Parse repository URL and return host, full name, and project name."""
    try:
        parsed_url = HttpUrl(url)
        if parsed_url.scheme not in ["http", "https"]:
            raise GitURLError(
                url,
                f"Unknown scheme provided: {parsed_url.scheme}",
            )
    except ValueError as e:
        raise GitURLError(url) from e

    assert (
        parsed_url.host and parsed_url.path
    ), f"Invalid Git repository URL: {parsed_url}"

    path_parts = parsed_url.path.strip("/").split("/")

    full_name = "/".join(path_parts[:2])

    host = parsed_url.host.split(".")[0].lower()

    host_domain = parsed_url.host

    name = path_parts[-1]

    return host_domain, host, name, full_name