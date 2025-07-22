import os
import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

import requests
from dotenv import load_dotenv

from osa_tool.utils import get_base_repo_url, logger

load_dotenv()


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

    # Platform
    platform: str


def detect_platform(repo_url: str) -> str:
    """Detect which platform the repository is hosted on.

    Args:
        repo_url: The URL of the Git repository.

    Raises:
        ValueError: If inappropriate platform used.
    """
    if "github.com" in repo_url:
        return "github"
    elif "gitlab" in repo_url:
        return "gitlab"
    elif "gitverse.ru" in repo_url:
        return "gitverse"
    else:
        raise ValueError(f"Unsupported platform for URL: {repo_url}")


def _parse_repository_metadata_github(repo_data: dict) -> RepositoryMetadata:
    """Parse GitHub API response into RepositoryMetadata."""
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
        platform="github",
    )


def _parse_repository_metadata_gitlab(repo_data: dict) -> RepositoryMetadata:
    """Parse GitLab API response into RepositoryMetadata."""
    owner_info = repo_data.get("owner", {}) or {}
    namespace = repo_data.get("namespace", {}) or {}

    # Converting to a unified view with GitHub
    created_time = datetime.strptime(repo_data.get("created_at", "").split(".")[0], "%Y-%m-%dT%H:%M:%S").strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    return RepositoryMetadata(
        name=repo_data.get("name", ""),
        full_name=repo_data.get("path_with_namespace", ""),
        owner=namespace.get("name", "") or owner_info.get("name", ""),
        owner_url=namespace.get("web_url", "") or owner_info.get("web_url", ""),
        description=repo_data.get("description", ""),
        stars_count=repo_data.get("star_count", 0),
        forks_count=repo_data.get("forks_count", 0),
        watchers_count=0,  # GitLab doesn't have watchers concept
        open_issues_count=repo_data.get("open_issues_count", 0),
        default_branch=repo_data.get("default_branch", ""),
        created_at=created_time,
        updated_at=repo_data.get("last_activity_at", ""),
        pushed_at=repo_data.get("last_activity_at", ""),
        size_kb=repo_data.get("repository_size", 0) // 1024,  # Convert bytes to KB
        clone_url_http=repo_data.get("http_url_to_repo", ""),
        clone_url_ssh=repo_data.get("ssh_url_to_repo", ""),
        contributors_url=f"{repo_data.get('web_url', '')}/contributors" if repo_data.get("web_url") else None,
        languages_url=f"{repo_data.get('web_url', '')}/languages" if repo_data.get("web_url") else "",
        issues_url=f"{repo_data.get('web_url', '')}/issues" if repo_data.get("web_url") else None,
        language="",  # GitLab API doesn't provide primary language in basic response
        languages=[],
        topics=repo_data.get("tag_list", []),
        has_wiki=repo_data.get("wiki_enabled", False),
        has_issues=repo_data.get("issues_enabled", False),
        has_projects=True,  # GitLab always has project management features
        is_private=repo_data.get("visibility", "public") != "public",
        homepage_url="",
        license_name="",
        license_url="",
        platform="gitlab",
    )


def _parse_repository_metadata_gitverse(repo_data: dict) -> RepositoryMetadata:
    """Parse Gitverse API response into RepositoryMetadata."""
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
        languages=repo_data.get("languages", []),
        topics=repo_data.get("topics", []) or [],
        has_wiki=repo_data.get("has_wiki", False),
        has_issues=repo_data.get("has_issues", False),
        has_projects=repo_data.get("has_projects", False),
        is_private=repo_data.get("private", False),
        homepage_url=repo_data.get("homepage", ""),
        license_name=repo_data.get("license", {}).get("name", ""),
        license_url=repo_data.get("license", {}).get("url", ""),
        platform="gitverse",
    )


@lru_cache(maxsize=1)
def load_data_metadata(repo_url: str) -> RepositoryMetadata | None:
    """Retrieve repository metadata from any supported platform."""
    try:
        platform = detect_platform(repo_url)
        base_url = get_base_repo_url(repo_url)

        if platform == "github":
            return _load_github_metadata(base_url)
        elif platform == "gitlab":
            return _load_gitlab_metadata(repo_url, base_url)
        else:
            return _load_gitverse_metadata(base_url)

    except Exception as exc:
        logger.error(f"Error while fetching repository metadata: {exc}")
        return None


def _load_github_metadata(base_url: str) -> RepositoryMetadata:
    """Load metadata from GitHub API."""
    headers = {
        "Authorization": f"token {os.getenv('GIT_TOKEN', os.getenv('GITHUB_TOKEN', ''))}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{base_url}"

    response = requests.get(url=url, headers=headers)
    response.raise_for_status()

    metadata = response.json()
    logger.info(f"Successfully fetched GitHub metadata for repository: {base_url}")
    return _parse_repository_metadata_github(metadata)


def _load_gitlab_metadata(repo_url: str, base_url: str) -> RepositoryMetadata:
    """Load metadata from GitLab API."""
    gitlab_instance = re.match(r"(https?://[^/]*gitlab[^/]*)", repo_url).group(1)

    headers = {
        "Authorization": f"Bearer {os.getenv('GITLAB_TOKEN', os.getenv('GIT_TOKEN'))}",
        "Content-Type": "application/json",
    }

    project_path = base_url.replace("/", "%2F")
    url = f"{gitlab_instance}/api/v4/projects/{project_path}"

    response = requests.get(url=url, headers=headers)
    response.raise_for_status()

    metadata = response.json()
    logger.info(f"Successfully fetched GitLab metadata for repository: {base_url}")
    return _parse_repository_metadata_gitlab(metadata)


def _load_gitverse_metadata(base_url: str) -> RepositoryMetadata:
    """Load metadata from Gitverse API."""
    headers = {
        "Authorization": f"Bearer {os.getenv('GITVERSE_TOKEN', os.getenv('GIT_TOKEN'))}",
        "Accept": "application/vnd.gitverse.object+json;version=1",
        "Content-Type": "application/json",
    }

    url = f"https://api.gitverse.ru/repos/{base_url}"

    response = requests.get(url=url, headers=headers)
    response.raise_for_status()

    metadata = response.json()
    logger.info(f"Successfully fetched Gitverse metadata for repository: {base_url}")
    return _parse_repository_metadata_gitverse(metadata)
