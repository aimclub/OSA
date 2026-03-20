import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

import requests
from dotenv import load_dotenv
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
        
        This method attempts to load metadata without authentication first. If that fails,
        it retries with authentication enabled. If an HTTP error occurs, it logs a detailed
        message based on the status code (e.g., authentication failure, repository not found,
        access denied) before re-raising the exception. Any other unexpected errors are also
        logged and re-raised.
        
        Args:
            repo_url: The full URL of the repository.
        
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
        
        This method must be implemented by subclasses to fetch and parse repository metadata (such as stars, forks, issues, and descriptions) from a specific hosting platform (e.g., GitHub, GitLab). It is abstract because each platform has a different API structure and authentication mechanism.
        
        Args:
            repo_url: The full URL of the repository.
            use_token: Whether to use an authentication token for the API request, which may allow higher rate limits or access to private repository data.
        
        Returns:
            Parsed repository metadata.
        """
        pass

    @classmethod
    @abstractmethod
    def _parse_metadata(cls, repo_data: dict) -> RepositoryMetadata:
        """
        Abstract method to parse raw API response dictionary into RepositoryMetadata.
        
        This method is implemented by subclasses to transform platform-specific API data into a standardized RepositoryMetadata object. It ensures that metadata from different sources (e.g., GitHub, GitLab) is normalized for consistent use throughout the OSA Tool pipeline.
        
        Args:
            repo_data: Raw API response data from a code hosting platform (e.g., GitHub, GitLab).
        
        Returns:
            RepositoryMetadata: Parsed and normalized repository metadata.
        """
        pass


class GitHubMetadataLoader(MetadataLoader):
    """
    GitHubMetadataLoader loads metadata from GitHub repositories via the GitHub API.
    
        Attributes:
            api_token: GitHub API token for authenticated requests.
            base_url: Base URL for the GitHub API.
            session: HTTP session for making API requests.
    
        Methods:
            _load_platform_data: Loads GitHub repository metadata via GitHub API.
            _parse_metadata: Parses GitHub API response into RepositoryMetadata.
    """

    @classmethod
    def _load_platform_data(cls, repo_url: str, use_token: bool) -> RepositoryMetadata:
        """
        Load GitHub repository metadata via GitHub API.
        
        This class method fetches raw repository data from the GitHub API and parses it into a structured metadata object. It supports authenticated requests using a token when required.
        
        Args:
            repo_url: URL of the GitHub repository.
            use_token: Boolean flag indicating whether to use an authentication token for the API request. If True, the token is read from environment variables ('GIT_TOKEN' or 'GITHUB_TOKEN').
        
        Returns:
            RepositoryMetadata: Parsed metadata object containing repository details.
        
        Why:
            Authentication (use_token) allows access to private repositories or higher rate limits. The method centralizes API interaction and error handling, ensuring consistent metadata retrieval for downstream processing.
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
        
        This class method extracts and structures repository metadata from the raw GitHub API response dictionary. It handles nested fields (like owner, license, and languages) and provides sensible defaults for missing values to ensure a complete RepositoryMetadata object is always returned.
        
        Args:
            repo_data (dict): Raw GitHub API response containing repository information.
        
        Returns:
            RepositoryMetadata: Parsed repository metadata object populated with fields such as name, owner details, counts (stars, forks, watchers, issues), URLs, timestamps, language data, topics, and license information.
        
        Why:
            The method centralizes the parsing logic to transform the varied and nested GitHub API response into a consistent, typed data structure (RepositoryMetadata). This ensures that downstream components receive a uniform object with validated fields and default values, improving reliability and maintainability across the OSA Tool's documentation pipeline.
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


class GitLabMetadataLoader(MetadataLoader):
    """
    GitLabMetadataLoader loads repository metadata from GitLab using its API.
    
        Attributes:
        - api_token: GitLab API token for authentication.
        - base_url: Base URL for GitLab API requests.
    
        Methods:
        - _load_platform_data: Retrieves repository data from GitLab API.
        - _parse_metadata: Converts raw API response into structured metadata object.
    """

    @classmethod
    def _load_platform_data(cls, repo_url: str, use_token: bool) -> RepositoryMetadata:
        """
        Load GitLab repository metadata via GitLab API.
        
        Args:
            repo_url: URL of the GitLab repository.
            use_token: Whether to include an authorization token in the request. If True, the token is read from the GITLAB_TOKEN or GIT_TOKEN environment variable.
        
        Returns:
            RepositoryMetadata: Parsed metadata object.
        
        Why:
            This method fetches repository metadata directly from the GitLab API, enabling the tool to obtain detailed, up-to-date information about the repository (such as stars, forks, issues, and license) without relying on local clones or cached data. Using an API token when available allows access to private repositories or higher rate limits.
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
        
        This class method transforms raw GitLab repository data into a standardized RepositoryMetadata object. It handles GitLab-specific field mappings, converts units (e.g., bytes to KB), and constructs derived URLs. WHY: GitLab's API structure differs from other platforms (like GitHub), so this method adapts its response to a common internal data model, filling in missing fields with defaults or calculated values.
        
        Args:
            repo_data: Raw GitLab API response dictionary for a repository.
        
        Returns:
            RepositoryMetadata: Parsed repository metadata with fields populated from repo_data. Notable adaptations include:
                - watchers_count is set to 0 (GitLab does not provide this).
                - size_kb is calculated by converting repository_size from bytes.
                - created_at is reformatted to a standard ISO timestamp.
                - URLs (contributors_url, languages_url, issues_url) are built from the web_url.
                - owner and owner_url are sourced from namespace or owner fields.
                - language is left empty and languages as an empty list (GitLab API does not provide primary language data).
                - has_projects is always True (GitLab projects inherently have project management).
                - is_private is determined from the visibility field.
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
    """
    GitverseMetadataLoader loads repository metadata from the Gitverse API.
    
        Methods:
            _load_platform_data: Loads Gitverse repository metadata via Gitverse API.
            _parse_metadata: Parses Gitverse API response into RepositoryMetadata.
    
        Attributes:
            api_base_url: Base URL for the Gitverse API.
            session: HTTP session for making API requests.
            timeout: Request timeout duration.
    
        The _load_platform_data method fetches raw metadata from the API using a repository URL. The _parse_metadata method converts the raw API response into a structured RepositoryMetadata object. The api_base_url attribute defines the API endpoint, the session manages HTTP connections, and the timeout controls request timing.
    """

    @classmethod
    def _load_platform_data(cls, repo_url: str, use_token: bool) -> RepositoryMetadata:
        """
        Load Gitverse repository metadata via Gitverse API.
        
        This class method fetches repository metadata from the Gitverse API by constructing a request with appropriate authentication and headers. It extracts the base repository path from the provided URL, calls the API, and parses the JSON response into a structured RepositoryMetadata object.
        
        Args:
            repo_url: URL of the Gitverse repository.
            use_token: Whether to use an authentication token from environment variables for the API request. If True, the token is included in the Authorization header; if False, the header may be omitted or use a placeholder.
        
        Returns:
            RepositoryMetadata: Parsed metadata object containing repository details such as name, owner, counts, URLs, timestamps, and license information.
        
        Why:
            The method enables the OSA Tool to retrieve standardized metadata from Gitverse-hosted repositories, which is essential for automated documentation generation and repository analysis. It handles authentication and API communication, ensuring reliable data fetching even when tokens are conditionally required.
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
        
        This class method extracts and transforms raw repository data from the Gitverse API into a structured RepositoryMetadata object. It handles nested fields (like owner and license) and provides safe defaults for missing values to ensure the metadata object is always valid.
        
        Args:
            repo_data: Raw Gitverse API response containing repository information.
        
        Returns:
            RepositoryMetadata: Parsed repository metadata with fields populated from the API response. Key fields include name, owner details, counts (stars, forks, watchers, issues), URLs, timestamps, repository settings, and license information.
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
