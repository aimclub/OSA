from git import Repo, GitCommandError, InvalidGitRepositoryError
import os
import logging
from rich.logging import RichHandler
import requests
from functools import lru_cache

from dotenv import load_dotenv
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)



def parse_folder_name(repo_url: str) -> str:
    """Parses the repository URL to extract the folder name.

    Args:
        repo_url: The URL of the GitHub repository.

    Returns:
        The name of the folder where the repository will be cloned.
    """
    return repo_url.rstrip("/").split("/")[-1]


def osa_project_root() -> Path:
    """Returns osa_tool project root folder."""
    return Path(__file__).parent.parent


def get_base_repo_url(repo_url: str) -> str:
    """Extracts the base repository URL path from a given GitHub URL.

    Args:
        repo_url (str, optional): The GitHub repository URL. If not provided,
            the instance's `repo_url` attribute is used. Defaults to None.

    Returns:
        str: The base repository path (e.g., 'username/repo-name').

    Raises:
        ValueError: If the provided URL does not start with 'https://github.com/'.
    """
    if repo_url.startswith("https://github.com/"):
        return repo_url[len("https://github.com/"):].rstrip('/')
    else:
        raise ValueError("Unsupported repository URL format.")



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
def load_data_metadata(repo_url: str):
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



logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

logger = logging.getLogger("rich")


class GithubAgent:
    """A class to interact with GitHub repositories.

    This class provides functionality to clone repositories, create and checkout branches,
    commit and push changes, and create pull requests.

    Attributes:
        AGENT_SIGNATURE: A signature string appended to pull request descriptions.
        repo_url: The URL of the GitHub repository.
        clone_dir: The directory where the repository will be cloned.
        branch_name: The name of the branch to be created or checked out.
        repo: The GitPython Repo object representing the repository.
        token: The GitHub token for authentication.
    """

    AGENT_SIGNATURE = (
        "\n\n---\n*This PR was created by [osa_tool](https://github.com/ITMO-NSS-team/Open-Source-Advisor).*"
        "\n_OSA just makes your open source project better!_"
    )

    def __init__(self, repo_url: str, branch_name: str = "osa_tool"):
        """Initializes the GithubAgent with the repository URL and branch name.

        Args:
            repo_url: The URL of the GitHub repository.
            branch_name: The name of the branch to be created. Defaults to "osa_tool".
        """
        load_dotenv()
        self.repo_url = repo_url
        self.clone_dir = parse_folder_name(repo_url)
        self.branch_name = branch_name
        self.repo = None
        self.token = os.getenv("GIT_TOKEN", "")
        self.fork_url = None
        self.metadata = load_data_metadata(self.repo_url)
        self.base_branch = self.metadata.default_branch

    def create_fork(self) -> None:
        """Creates a fork of the repository in the osa_tool account.

        Raises:
            ValueError: If the GitHub token is not set or the API request fails.
        """
        if not self.token:
            raise ValueError("GitHub token is required to create a fork.")

        base_repo = get_base_repo_url(self.repo_url)
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        url = f"https://api.github.com/repos/{base_repo}/forks"
        response = requests.post(url, headers=headers)

        if response.status_code in {200, 202}:
            self.fork_url = response.json()['html_url']
            logger.info(f"Fork created successfully: {self.fork_url}")
        else:
            logger.error(f"Failed to create fork: {response.status_code} - {response.text}")
            raise ValueError("Failed to create fork.")

    def star_repository(self) -> None:
        """Stars the GitHub repository if it is not already starred.

        Raises:
            ValueError: If the GitHub token is not set or the API request fails.
        """
        if not self.token:
            raise ValueError("GitHub token is required to star the repository.")

        base_repo = get_base_repo_url(self.repo_url)
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Check if the repository is already starred
        url_check = f"https://api.github.com/user/starred/{base_repo}"
        response_check = requests.get(url_check, headers=headers)

        if response_check.status_code == 204:
            logger.info(f"Repository {base_repo} is already starred.")
            return
        elif response_check.status_code != 404:
            logger.error(f"Failed to check star status: {response_check.status_code} - {response_check.text}")
            raise ValueError("Failed to check star status.")

        # Star the repository
        url_star = f"https://api.github.com/user/starred/{base_repo}"
        response_star = requests.put(url_star, headers=headers)

        if response_star.status_code == 204:
            logger.info(f"Repository {base_repo} has been starred successfully.")
        else:
            logger.error(f"Failed to star repository: {response_star.status_code} - {response_star.text}")
            raise ValueError("Failed to star repository.")

    def clone_repository(self) -> None:
        """Clones the repository into the specified directory.

        If the repository already exists locally, it initializes the repository.
        If the directory exists but is not a valid Git repository, an error is raised.

        Raises:
            InvalidGitRepositoryError: If the local directory is not a valid Git repository.
            GitCommandError: If cloning the repository fails.
        """
        if self.repo:
            logger.warning(f"Repository is already initialized ({self.repo_url})")
            return

        if os.path.exists(self.clone_dir):
            try:
                logger.info(f"Repository already exists at {self.clone_dir}. Initializing...")
                self.repo = Repo(self.clone_dir)
                logger.info("Repository initialized from existing directory")
            except InvalidGitRepositoryError:
                logger.error(f"Directory {self.clone_dir} exists but is not a valid Git repository")
                raise
        else:
            try:
                logger.info(f"Cloning repository {self.repo_url} into {self.clone_dir}...")
                self.repo = Repo.clone_from(self._get_auth_url(), self.clone_dir)
                logger.info("Cloning completed")
            except GitCommandError as e:
                logger.error(f"Cloning failed: {repr(e)}")
                raise

    def create_and_checkout_branch(self) -> None:
        """Creates and checks out a new branch.

        If the branch already exists, it simply checks out the branch.
        """
        if self.branch_name in self.repo.heads:
            logger.info(f"Branch {self.branch_name} already exists. Switching to it...")
            self.repo.git.checkout(self.branch_name)
            return
        else:
            logger.info(f"Creating and switching to branch {self.branch_name}...")
            self.repo.git.checkout('-b', self.branch_name)
            logger.info(f"Switched to branch {self.branch_name}.")

    def commit_and_push_changes(self, commit_message: str = "osa_tool recommendations") -> None:
        """Commits and pushes changes to the forked repository.

        Args:
            commit_message: The commit message. Defaults to "osa_tool recommendations".
        """
        if not self.fork_url:
            raise ValueError("Fork URL is not set. Please create a fork first.")

        logger.info("Committing changes...")
        self.repo.git.add('.')
        self.repo.git.commit('-m', commit_message)
        logger.info("Commit completed.")

        logger.info(f"Pushing changes to branch {self.branch_name} in fork...")
        self.repo.git.remote('set-url', 'origin', self._get_auth_url(self.fork_url))
        self.repo.git.push('--set-upstream', 'origin', self.branch_name, force_with_lease=True)
        logger.info("Push completed.")

    def create_pull_request(self, title: str = None, body: str = None) -> None:
        """Creates a pull request from the forked repository to the original repository.

        Args:
            title: The title of the PR. If None, the commit message will be used.
            body: The body/description of the PR. If None, the commit message with agent signature will be used.

        Raises:
            ValueError: If the GitHub token is not set or the API request fails.
        """
        if not self.token:
            raise ValueError("GitHub token is required to create a pull request.")

        base_repo = get_base_repo_url(self.repo_url)
        last_commit = self.repo.head.commit
        pr_title = title if title else last_commit.message
        pr_body = body if body else last_commit.message
        pr_body += self.AGENT_SIGNATURE

        pr_data = {
            "title": pr_title,
            "head": f"{self.fork_url.split('/')[-2]}:{self.branch_name}",
            "base": self.base_branch,
            "body": pr_body
        }

        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"https://api.github.com/repos/{base_repo}/pulls"
        response = requests.post(url, json=pr_data, headers=headers)

        if response.status_code == 201:
            logger.info(f"Pull request created successfully: {response.json()['html_url']}")
        else:
            logger.error(f"Failed to create pull request: {response.status_code} - {response.text}")
            if not "pull request already exists" in response.text:
                raise ValueError("Failed to create pull request.")

    def _get_auth_url(self, url: str = None) -> str:
        """Converts the repository URL by adding a token for authentication.

        Args:
            url: The URL to convert. If None, uses the original repository URL.

        Returns:
            The repository URL with the token.

        Raises:
            ValueError: If the token is not found or the repository URL format is unsupported.
        """
        if not self.token:
            raise ValueError("Token not found in environment variables.")

        repo_url = url if url else self.repo_url
        if repo_url.startswith("https://github.com/"):
            repo_path = repo_url[len("https://github.com/"):]
            auth_url = f"git@github.com:{repo_path}.git"
            return auth_url
        else:
            raise ValueError("Unsupported repository URL format.")
