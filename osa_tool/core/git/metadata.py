import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Counter

import requests
from dotenv import load_dotenv
from git import Repo
from requests import HTTPError

from osa_tool.utils.logger import logger
from osa_tool.utils.utils import get_base_repo_url

load_dotenv()


@dataclass
class RepositoryMetadata:
    """
    Dataclass to store Git repository metadata.
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


class MetadataLoader(ABC):
    """
    Abstract base class for repository metadata loaders.
    """

    @classmethod
    def load_data(cls, repo_url: str) -> RepositoryMetadata:
        """
        General method to load repository metadata for a given URL.
        Calls the platform-specific loader method.

        Args:
            repo_url (str): The full URL of the repository.

        Returns:
            RepositoryMetadata: Parsed repository metadata.
        """
        try:
            return cls._load_platform_data(repo_url, use_token=False)
        except Exception:
            try:
                return cls._load_platform_data(repo_url, use_token=True)

            except HTTPError as http_exc:
                status_code = getattr(http_exc.response, "status_code", None)
                logger.error(f"Error while fetching repository metadata: {http_exc}")

                if status_code == 401:
                    logger.error("Authentication failed: please check your Git token (missing or expired).")
                elif status_code == 404:
                    logger.error("Repository not found: please check the repository URL.")
                elif status_code == 403:
                    logger.error("Access denied: your token may lack sufficient permissions or you hit a rate limit.")
                else:
                    logger.error("Unexpected HTTP error occurred while accessing the repository metadata.")
                raise

            except Exception as exc:
                logger.error(f"Unexpected error while fetching repository metadata: {exc}")
                raise

    @classmethod
    @abstractmethod
    def _load_platform_data(cls, repo_url: str, use_token: bool) -> RepositoryMetadata:
        """
        Abstract method to load metadata from a platform-specific API.

        Args:
            repo_url (str): The full URL of the repository.
            use_token (bool): Whether to use authentication token.

        Returns:
            RepositoryMetadata: Parsed repository metadata.
        """
        pass

    @classmethod
    @abstractmethod
    def _parse_metadata(cls, repo_data: dict) -> RepositoryMetadata:
        """
        Abstract method to parse raw API response dictionary into RepositoryMetadata.

        Args:
            repo_data (dict): Raw API response data.

        Returns:
            RepositoryMetadata: Parsed repository metadata.
        """
        pass


class GitHubMetadataLoader(MetadataLoader):
    @classmethod
    def _load_platform_data(cls, repo_url: str, use_token: bool) -> RepositoryMetadata:
        """
        Load GitHub repository metadata via GitHub API.

        Args:
            repo_url (str): URL of the GitHub repository.

        Returns:
            RepositoryMetadata: Parsed metadata object.
        """
        base_url = get_base_repo_url(repo_url)
        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        if use_token:
            headers["Authorization"] = f"token {os.getenv('GIT_TOKEN', os.getenv('GITHUB_TOKEN', ''))}"

        url = f"https://api.github.com/repos/{base_url}"
        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched GitHub metadata for repository: '{base_url}'")
        return GitHubMetadataLoader._parse_metadata(data)

    @classmethod
    def _parse_metadata(cls, repo_data: dict) -> RepositoryMetadata:
        """
        Parse GitHub API response into RepositoryMetadata.

        Args:
            repo_data (dict): Raw GitHub API response.

        Returns:
            RepositoryMetadata: Parsed repository metadata.
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

FILE_MAP = {"makefile": "Makefile", "dockerfile": "Dockerfile", "cmakelists.txt": "CMake", "jenkinsfile": "Groovy"}
EXT_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".cpp": "C++",
    ".hpp": "C++",
    ".c": "C",
    ".h": "C/C++",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".kt": "Kotlin",
    ".swift": "Swift",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".sh": "Shell",
    ".html": "HTML",
    ".css": "CSS",
    ".sql": "SQL",
    ".jsx": "React JSX",
    ".tsx": "React TSX",
    ".vue": "Vue",
}
LICENSE_NAMES = {'license', 'copying', 'license.md', 'license.txt', 'copying.md'}

class LocalMetadataLoader(MetadataLoader):
    @classmethod
    def _load_platform_data(cls, repo_url: str, use_token: bool) -> RepositoryMetadata:
        cls.repo = Repo(repo_url)
        cls.repo_path = repo_url

        basename = os.path.basename(repo_url)
        owner = cls.repo.config_reader().get("user", "name")
        dates = cls._load_dates()
        size = cls._get_repository_size()
        languages = cls._get_languages()
        remotes = cls._get_remotes()
        default_branch = cls._get_default_branch()
        license_name = cls._find_license()

        return RepositoryMetadata(
            name=basename,
            full_name=basename,
            owner=owner,
            owner_url=None,
            description=None,
            stars_count=0,
            forks_count=0,
            watchers_count=0,
            open_issues_count=0,
            default_branch=default_branch,
            created_at=dates['created_at'],
            updated_at=dates['updated_at'],
            pushed_at=dates['pushed_at'],
            size_kb=size,
            clone_url_http=remotes["clone_url_http"],
            clone_url_ssh=remotes["clone_url_ssh"],
            contributors_url=None,
            languages_url="",
            issues_url=None,
            language=languages[0] if languages else None,
            languages=languages,
            topics=[],
            has_wiki=False,
            has_issues=False,
            has_projects=False,
            is_private=False,
            homepage_url=None,
            license_name=license_name,
            license_url=None,
        )

    @classmethod
    def _find_license(cls) -> str | None:
        files = [f for f in cls.repo.git.ls_files().split('\n') if '/' not in f]
        license_file = None
        for f in files:
            if f.lower() in LICENSE_NAMES:
                license_file = f
                break

        if license_file:
            full_path = os.path.join(cls.repo_path, license_file)
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read(500)

                if re.search(r'MIT', content, re.I):
                    return "MIT"
                if re.search(r'Apache', content, re.I):
                    return "Apache 2.0"
                if re.search(r'GNU|GPL', content, re.I):
                    return "GPL"
                if re.search(r'BSD', content, re.I):
                    return "BSD"

        return None


    @classmethod
    def _load_dates(cls) -> dict[str, str]:
        first_commit_time = next(cls.repo.iter_commits(reverse=True, max_count=1)).committed_datetime
        last_commit_time = cls.repo.head.commit.committed_datetime
        time_format = "%Y-%m-%dT%H:%M:%SZ"

        return {
            "created_at": first_commit_time.strftime(time_format),
            "updated_at": last_commit_time.strftime(time_format),
            "pushed_at": last_commit_time.strftime(time_format),
        }

    @classmethod
    def _get_repository_size(cls) -> int:
        total_bytes = 0

        files = cls.repo.git.ls_files().split("\n")

        for file_path in files:
            full_path = os.path.join(cls.repo_path, file_path)
            if os.path.exists(full_path):
                total_bytes += os.path.getsize(full_path)

        return round(total_bytes / 1024)

    @classmethod
    def _get_languages(cls) -> list[str]:
        files = cls.repo.git.ls_files().split("\n")

        weights = Counter()

        for f in files:
            if not f:
                continue

            abs_path = os.path.join(cls.repo_path, f)
            if not os.path.isfile(abs_path):
                continue

            name = os.path.basename(f).lower()
            ext = os.path.splitext(name)[1].lower()

            lang = FILE_MAP.get(name) or EXT_MAP.get(ext)

            if lang:
                weights[lang] += os.path.getsize(abs_path)

        return sorted(weights, key=weights.get, reverse=True)

    @classmethod
    def _get_remotes(cls) -> dict[str, str]:
        http_url = ""
        ssh_url = ""
        for remote in cls.repo.remotes:
            remote_data = {"name": remote.name, "ssh_url": None, "http_url": None}

            for url in remote.urls:
                if url.startswith("http"):
                    http_url = url
                elif url.startswith("git@") or url.startswith("ssh://"):
                    ssh_url = url
        return {
            "clone_url_http": http_url,
            "clone_url_ssh": ssh_url,
        }

    @classmethod
    def _get_default_branch(cls) -> str:
        local_branches = [b.name for b in cls.repo.heads]

        for priority_name in ['master', 'main']:
            if priority_name in local_branches:
                return priority_name

        if not cls.repo.head.is_detached:
            return cls.repo.active_branch.name
        if local_branches:
            return local_branches[0]
        raise ValueError("Repository has no default branch")

    @classmethod
    def _parse_metadata(cls, repo_data: dict) -> RepositoryMetadata:
        pass


class GitLabMetadataLoader(MetadataLoader):
    @classmethod
    def _load_platform_data(cls, repo_url: str, use_token: bool) -> RepositoryMetadata:
        """
        Load GitLab repository metadata via GitLab API.

        Args:
            repo_url (str): URL of the GitLab repository.

        Returns:
            RepositoryMetadata: Parsed metadata object.
        """
        base_url = get_base_repo_url(repo_url)
        gitlab_instance_match = re.match(r"(https?://[^/]*gitlab[^/]*)", repo_url)
        if not gitlab_instance_match:
            raise ValueError("Invalid GitLab repository URL")
        gitlab_instance = gitlab_instance_match.group(1)

        headers = {
            "Content-Type": "application/json",
        }

        if use_token:
            headers["Authorization"] = f"Bearer {os.getenv('GITLAB_TOKEN', os.getenv('GIT_TOKEN'))}"

        project_path = base_url.replace("/", "%2F")
        url = f"{gitlab_instance}/api/v4/projects/{project_path}"

        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched GitLab metadata for repository: '{base_url}'")
        return GitLabMetadataLoader._parse_metadata(data)

    @classmethod
    def _parse_metadata(cls, repo_data: dict) -> RepositoryMetadata:
        """
        Parse GitLab API response into RepositoryMetadata.

        Args:
            repo_data (dict): Raw GitLab API response.

        Returns:
            RepositoryMetadata: Parsed repository metadata.
        """
        owner_info = repo_data.get("owner", {}) or {}
        namespace = repo_data.get("namespace", {}) or {}

        created_raw = repo_data.get("created_at", "")
        if created_raw:
            created_time = datetime.strptime(created_raw.split(".")[0], "%Y-%m-%dT%H:%M:%S").strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        else:
            created_time = ""

        return RepositoryMetadata(
            name=repo_data.get("name", ""),
            full_name=repo_data.get("path_with_namespace", ""),
            owner=namespace.get("name", "") or owner_info.get("name", ""),
            owner_url=namespace.get("web_url", "") or owner_info.get("web_url", ""),
            description=repo_data.get("description", ""),
            stars_count=repo_data.get("star_count", 0),
            forks_count=repo_data.get("forks_count", 0),
            watchers_count=0,  # GitLab does not have watchers, set to 0
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
            language="",  # GitLab API does not provide primary language
            languages=[],
            topics=repo_data.get("tag_list", []),
            has_wiki=repo_data.get("wiki_enabled", False),
            has_issues=repo_data.get("issues_enabled", False),
            has_projects=True,  # GitLab always has project management features enabled
            is_private=repo_data.get("visibility", "public") != "public",
            homepage_url="",
            license_name="",
            license_url="",
        )


class GitverseMetadataLoader(MetadataLoader):
    @classmethod
    def _load_platform_data(cls, repo_url: str, use_token: bool) -> RepositoryMetadata:
        """
        Load Gitverse repository metadata via Gitverse API.

        Args:
            repo_url (str): URL of the Gitverse repository.

        Returns:
            RepositoryMetadata: Parsed metadata object.
        """
        base_url = get_base_repo_url(repo_url)
        headers = {
            "Authorization": f"Bearer {os.getenv('GITVERSE_TOKEN', os.getenv('GIT_TOKEN'))}",
            "Accept": "application/vnd.gitverse.object+json;version=1",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
        url = f"https://api.gitverse.ru/repos/{base_url}"

        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
        data = response.json()
        logger.info(f"Successfully fetched Gitverse metadata for repository: '{base_url}'")
        return GitverseMetadataLoader._parse_metadata(data)

    @classmethod
    def _parse_metadata(cls, repo_data: dict) -> RepositoryMetadata:
        """
        Parse Gitverse API response into RepositoryMetadata.

        Args:
            repo_data (dict): Raw Gitverse API response.

        Returns:
            RepositoryMetadata: Parsed repository metadata.
        """
        owner_info = repo_data.get("owner", {}) or {}
        license_info = repo_data.get("license", {}) or {}

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
            languages=repo_data.get("languages", []) or [],
            topics=repo_data.get("topics", []) or [],
            has_wiki=repo_data.get("has_wiki", False),
            has_issues=repo_data.get("has_issues", False),
            has_projects=repo_data.get("has_projects", False),
            is_private=repo_data.get("private", False),
            homepage_url=repo_data.get("homepage", ""),
            license_name=license_info.get("name", ""),
            license_url=license_info.get("url", ""),
        )
