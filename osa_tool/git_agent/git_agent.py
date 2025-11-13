import abc
import os
import re
import requests
import time

from dotenv import load_dotenv
from git import GitCommandError, InvalidGitRepositoryError, Repo
from typing import List

from osa_tool.analytics.metadata import (
    RepositoryMetadata,
    GitHubMetadataLoader,
    GitLabMetadataLoader,
    GitverseMetadataLoader,
)
from osa_tool.logger import logger
from osa_tool.utils import get_base_repo_url, parse_folder_name


class GitAgent(abc.ABC):
    """Abstract base class for Git platform agents.

    This class provides functionality to clone repositories, create and checkout branches,
    commit and push changes, and create pull requests.

    Attributes:
        AGENT_SIGNATURE: A signature string appended to pull request descriptions.
        repo_url: The URL of the Git repository.
        clone_dir: The directory where the repository will be cloned.
        branch_name: The name of the branch to be created.
        repo: The GitPython Repo object representing the repository.
        token: The Git token for authentication.
        fork_url: The URL of the created fork of a Git repository.
        metadata: Git repository metadata.
        base_branch: The name of the repository's branch.
        pr_report_body: A formatted message for a pull request.
    """

    AGENT_SIGNATURE = (
        "\n\n---\n*This PR was created by [osa_tool](https://github.com/aimclub/OSA).*"
        "\n_OSA just makes your open source project better!_"
    )

    def __init__(self, repo_url: str, repo_branch_name: str = None, branch_name: str = "osa_tool"):
        """Initializes the agent with repository info.

        Args:
            repo_url: The URL of the GitHub repository.
            repo_branch_name: The name of the repository's branch to be checked out.
            branch_name: The name of the branch to be created. Defaults to "osa_tool".
        """
        load_dotenv()
        self.repo_url = repo_url
        self.clone_dir = os.path.join(os.getcwd(), parse_folder_name(repo_url))
        self.branch_name = branch_name
        self.repo = None
        self.token = self._get_token()
        self.fork_url = None
        self.metadata = self._load_metadata(self.repo_url)
        self.base_branch = repo_branch_name or self.metadata.default_branch
        self.pr_report_body = ""

    @abc.abstractmethod
    def _get_token(self) -> str:
        """Return platform-specific token from environment."""
        pass

    @abc.abstractmethod
    def _load_metadata(self, repo_url: str) -> RepositoryMetadata:
        """Return platform-specific repository metadata.

        Args:
            repo_url: The URL of the Git repository.
        """
        pass

    @abc.abstractmethod
    def create_fork(self) -> None:
        """Create a fork of the repository."""
        pass

    @abc.abstractmethod
    def star_repository(self) -> None:
        """Star the repository on the platform."""
        pass

    @abc.abstractmethod
    def create_pull_request(self, title: str = None, body: str = None) -> None:
        """Create a pull request / merge request on the platform.

        Args:
            title: The title of the PR. If None, the commit message will be used.
            body: The body/description of the PR. If None, the commit message with agent signature will be used.
        """
        pass

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
                logger.info(
                    f"Cloning the '{self.base_branch}' branch from {self.repo_url} into directory {self.clone_dir}..."
                )
                self.repo = Repo.clone_from(
                    url=self._get_unauth_url(),
                    to_path=self.clone_dir,
                    branch=self.base_branch,
                    single_branch=True,
                )
                logger.info("Cloning completed")

            except Exception:
                try:
                    logger.info(
                        f"Cloning the '{self.base_branch}' branch from {self.repo_url} into directory {self.clone_dir}..."
                    )
                    self.repo = Repo.clone_from(
                        url=self._get_auth_url(),
                        to_path=self.clone_dir,
                        branch=self.base_branch,
                        single_branch=True,
                    )
                    logger.info("Cloning completed")
                except GitCommandError as e:
                    stderr = e.stderr or ""
                    logger.error(f"Cloning failed: {e}")

                    if "remote branch" in stderr and "not found" in stderr:
                        logger.error(
                            f"Branch '{self.base_branch}' not found in the remote repository. Please check the branch name."
                        )
                    else:
                        logger.error("An unexpected Git error occurred while cloning the repository.")
                    raise Exception(f"Cannot clone the repository: {self.repo_url}") from e

    def create_and_checkout_branch(self, branch: str = None) -> None:
        """Creates and checks out a new branch.

        If the branch already exists, it simply checks out the branch.

        Args:
            branch: The name of the branch to create or check out. Defaults to `branch_name`.
        """
        if branch is None:
            branch = self.branch_name

        if branch in self.repo.heads:
            logger.info(f"Branch {branch} already exists. Switching to it...")
            self.repo.git.checkout(branch)
            return
        else:
            logger.info(f"Creating and switching to branch {branch}...")
            self.repo.git.checkout("-b", branch)
            logger.info(f"Switched to branch {branch}.")

    def commit_and_push_changes(
        self,
        branch: str = None,
        commit_message: str = "osa_tool recommendations",
        force: bool = False,
    ) -> bool:
        """Commits and pushes changes to the forked repository.

        Args:
            branch: The name of the branch to push changes to. Defaults to `branch_name`.
            commit_message: The commit message. Defaults to "osa_tool recommendations".
            force: Option to force push the commit. Defaults to `False`
        """
        if not self.fork_url:
            raise ValueError("Fork URL is not set. Please create a fork first.")
        if branch is None:
            branch = self.branch_name

        logger.info("Committing changes...")
        self.repo.git.add(".")

        try:
            self.repo.git.commit("-m", commit_message)
            logger.info("Commit completed.")
        except GitCommandError as e:
            if "nothing to commit" in str(e):
                logger.warning("Nothing to commit: working tree clean")
                if self.pr_report_body:
                    logger.info(self.pr_report_body)
                return False
            else:
                raise

        logger.info(f"Pushing changes to branch {branch} in fork...")
        self.repo.git.remote("set-url", "origin", self._get_auth_url(self.fork_url))
        try:
            self.repo.git.push(
                "--set-upstream",
                "origin",
                branch,
                force_with_lease=not force,
                force=force,
            )
            logger.info("Push completed.")
            return True
        except GitCommandError as e:
            logger.error(
                f"""Push failed: Branch '{branch}' already exists in the fork.
                 To resolve this, please either:
                   1. Choose a different branch name that doesn't exist in the fork 
                      by modifying the `branch_name` parameter.
                   2. Delete the existing branch from forked repository.
                   3. Delete the fork entirely."""
            )
            return False

    def upload_report(
        self,
        report_filename: str,
        report_filepath: str,
        report_branch: str = "osa_tool_attachments",
        commit_message: str = "docs: upload pdf report",
    ) -> None:
        """Uploads the generated PDF report to a separate branch.

        Args:
            report_filename: Name of the report file.
            report_filepath: Path to the report file.
            report_branch: Name of the branch for storing reports. Defaults to "osa_tool_attachments".
            commit_message: Commit message for the report upload. Defaults to "upload pdf report".
        """
        logger.info("Uploading report...")

        with open(report_filepath, "rb") as f:
            report_content = f.read()
        self.create_and_checkout_branch(report_branch)

        with open(os.path.join(self.clone_dir, report_filename), "wb") as f:
            f.write(report_content)
        self.commit_and_push_changes(branch=report_branch, commit_message=commit_message, force=True)

        self.create_and_checkout_branch(self.branch_name)

        report_url = self._build_report_url(report_branch, report_filename)
        self.pr_report_body = f"\nGenerated report - [{report_filename}]({report_url})\n"

    @abc.abstractmethod
    def _build_report_url(self, report_branch: str, report_filename: str) -> str:
        """Returns the URL to the report file on the corresponding platform.

        Args:
            report_branch: Name of the branch for storing reports. Defaults to "osa_tool_attachments".
            report_filename: Name of the report file.
        """
        pass

    def update_about_section(self, about_content: dict) -> None:
        """Tries to update the 'About' section of the base and fork repository with the provided content.

        Args:
            about_content: Dictionary containing the metadata to update about section.

        Raises:
            ValueError: If the Git token is not set or inappropriate platform used.
        """
        if not self.token:
            raise ValueError("Git-platform token is required to fill repository's 'About' section.")
        if not self.fork_url:
            raise ValueError("Fork URL is not set. Please create a fork first.")

        base_repo = get_base_repo_url(self.repo_url)
        logger.info(f"Updating 'About' section for base repository - {self.repo_url}")
        self._update_about_section(base_repo, about_content)

        fork_repo = get_base_repo_url(self.fork_url)
        logger.info(f"Updating 'About' section for the fork - {self.fork_url}")
        self._update_about_section(fork_repo, about_content)

    @abc.abstractmethod
    def _update_about_section(self, repo_path: str, about_content: dict) -> None:
        """A platform-specific helper method for updating the About section of a repository.

        Args:
            repo_path: The base repository path (e.g., 'username/repo-name').
            about_content: Dictionary containing the metadata to update about section.
        """
        pass

    def _get_unauth_url(self, url: str = None) -> str:
        """Returns the repository URL without authentication token.

        Args:
            url: The URL to convert. If None, uses the original repository URL.

        Returns:
            The repository URL without authentication token.
        """
        repo_url = url if url else self.repo_url

        # Ensure the URL ends with .git
        if not repo_url.endswith(".git"):
            repo_url += ".git"

        return repo_url

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
        return self._build_auth_url(repo_url)

    @abc.abstractmethod
    def _build_auth_url(self, repo_url: str) -> str:
        """A platform-specific helper method for converting the repository URL by adding a token for authentication.

        Args:
            repo_url: The URL of the Git repository.
        """
        pass

    @abc.abstractmethod
    def validate_topics(self, topics: List[str]) -> List[str]:
        """Validates topics against platform-specific APIs.

        Args:
            topics (List[str]): List of potential topics to validate

        Returns:
            List[str]: List of validated topics that exist on platform
        """
        pass


class GitHubAgent(GitAgent):
    def _get_token(self) -> str:
        return os.getenv("GIT_TOKEN", os.getenv("GITHUB_TOKEN", ""))

    def _load_metadata(self, repo_url: str) -> RepositoryMetadata:
        return GitHubMetadataLoader.load_data(repo_url)

    def create_fork(self) -> None:
        if not self.token:
            raise ValueError("GitHub token is required to create a fork.")

        base_repo = get_base_repo_url(self.repo_url)
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = f"https://api.github.com/repos/{base_repo}/forks"
        response = requests.post(url, headers=headers)
        if response.status_code in {200, 202}:
            self.fork_url = response.json()["html_url"]
            logger.info(f"GitHub fork created successfully: {self.fork_url}")
        else:
            logger.error(f"Failed to create GitHub fork: {response.status_code} - {response.text}")
            raise ValueError("Failed to create fork.")

    def star_repository(self) -> None:
        if not self.token:
            raise ValueError("GitHub token is required to star the repository.")

        base_repo = get_base_repo_url(self.repo_url)
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        url = f"https://api.github.com/user/starred/{base_repo}"
        response_check = requests.get(url, headers=headers)
        if response_check.status_code == 204:
            logger.info(f"GitHub repository '{base_repo}' is already starred.")
            return
        elif response_check.status_code != 404:
            logger.error(f"Failed to check star status: {response_check.status_code} - {response_check.text}")
            raise ValueError("Failed to check star status.")

        response_star = requests.put(url, headers=headers)
        if response_star.status_code == 204:
            logger.info(f"GitHub repository '{base_repo}' has been starred successfully.")
        else:
            logger.error(f"Failed to star repository: {response_star.status_code} - {response_star.text}")
            raise ValueError("Failed to star repository.")

    def create_pull_request(self, title: str = None, body: str = None) -> None:
        if not self.token:
            raise ValueError("GIT_TOKEN or GITHUB_TOKEN token is required to create a pull request.")

        base_repo = get_base_repo_url(self.repo_url)
        last_commit = self.repo.head.commit
        pr_title = title if title else last_commit.message
        pr_body = body if body else last_commit.message
        pr_body += self.pr_report_body
        pr_body += self.AGENT_SIGNATURE

        pr_data = {
            "title": pr_title,
            "head": f"{self.fork_url.split('/')[-2]}:{self.branch_name}",
            "base": self.base_branch,
            "body": pr_body,
            "maintainer_can_modify": True,
        }
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = f"https://api.github.com/repos/{base_repo}/pulls"
        response = requests.post(url, json=pr_data, headers=headers)
        if response.status_code == 201:
            logger.info(f"GitHub pull request created successfully: {response.json()['html_url']}")
        else:
            logger.error(f"Failed to create pull request: {response.status_code} - {response.text}")
            if "pull request already exists" not in response.text:
                raise ValueError("Failed to create pull request.")

    def _update_about_section(self, repo_path: str, about_content: dict) -> None:
        url = f"https://api.github.com/repos/{repo_path}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"token {self.token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        }
        about_data = {
            "description": about_content["description"],
            "homepage": about_content["homepage"],
        }
        response = requests.patch(url, headers=headers, json=about_data)
        if response.status_code in {200, 201}:
            logger.info(f"Successfully updated GitHub repository description and homepage for '{repo_path}'.")
        else:
            logger.error(f"{response.status_code} - Failed to update description and homepage for '{repo_path}'.")

        url = f"https://api.github.com/repos/{repo_path}/topics"
        topics_data = {"names": about_content["topics"]}
        response = requests.put(url, headers=headers, json=topics_data)
        if response.status_code in {200, 201}:
            logger.info(f"Successfully updated GitHub repository topics for '{repo_path}'")
        else:
            logger.error(f"{response.status_code} - Failed to update topics for '{repo_path}'.")

    def _build_report_url(self, report_branch: str, report_filename: str) -> str:
        return f"{self.fork_url}/blob/{report_branch}/{report_filename}"

    def _build_auth_url(self, repo_url: str) -> str:
        if repo_url.startswith("https://github.com/"):
            repo_path = repo_url[len("https://github.com/") :]
            return f"https://{self.token}@github.com/{repo_path}.git"
        raise ValueError(f"Unsupported repository URL format for GitHub: {repo_url}")

    def validate_topics(self, topics: List[str]) -> List[str]:
        logger.info("Validating topics against GitHub Topics API...")
        min_repo = 5
        validated_topics = []

        for topic in topics:
            try:
                response = requests.get(
                    f"https://api.github.com/search/topics?q={topic}+repositories:>{min_repo}",
                    headers={"Accept": "application/vnd.github.v3+json"},
                )

                if response.status_code == 200:
                    data = response.json()
                    if (total := data.get("total_count", 0)) > 0:
                        if total == 1:
                            valid_topic = data.get("items")[0].get("name")
                            logger.debug(f"Applied transformation for topic: '{topic} -> {valid_topic}'")
                        else:
                            valid_topic = topic
                        validated_topics.append(valid_topic)
                    else:
                        logger.debug(f"Generated topic '{topic}' is not valid, skipping")
                elif response.status_code == 403:
                    logger.warning("Rate limit exceeded, waiting 60 seconds")
                    time.sleep(60)

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error validating topic '{topic}': {e}")
                continue

        logger.info(f"Validated {len(validated_topics)} topics out of {len(topics)}.")
        return validated_topics


class GitLabAgent(GitAgent):
    def _get_token(self) -> str:
        return os.getenv("GITLAB_TOKEN", os.getenv("GIT_TOKEN", ""))

    def _load_metadata(self, repo_url: str) -> RepositoryMetadata:
        return GitLabMetadataLoader.load_data(repo_url)

    def create_fork(self) -> None:
        if not self.token:
            raise ValueError("GitLab token is required to create a fork.")
        gitlab_instance = re.match(r"(https?://[^/]*gitlab[^/]*)", self.repo_url).group(1)
        base_repo = get_base_repo_url(self.repo_url)
        project_path = base_repo.replace("/", "%2F")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        user_url = f"{gitlab_instance}/api/v4/user"
        user_response = requests.get(user_url, headers=headers)
        if user_response.status_code != 200:
            logger.error(f"Failed to get user info: {user_response.status_code} - {user_response.text}")
            raise ValueError("Failed to get user information.")
        current_username = user_response.json().get("username", "")

        if current_username == self.metadata.owner:
            self.fork_url = self.repo_url
            logger.info(f"User '{current_username}' already owns the repository. Using original URL: {self.fork_url}")
            return

        forks_url = f"{gitlab_instance}/api/v4/projects/{project_path}/forks"
        forks_response = requests.get(forks_url, headers=headers)
        if forks_response.status_code != 200:
            logger.error(f"Failed to get forks: {forks_response.status_code} - {forks_response.text}")
            raise ValueError("Failed to get forks list.")

        forks = forks_response.json()
        for fork in forks:
            namespace = fork.get("namespace", {})
            fork_owner = namespace.get("name") or namespace.get("path") or ""
            if fork_owner == current_username:
                self.fork_url = fork["web_url"]
                logger.info(f"Fork already exists: {self.fork_url}")
                return

        fork_url = f"{gitlab_instance}/api/v4/projects/{project_path}/fork"
        fork_response = requests.post(fork_url, headers=headers)
        if fork_response.status_code in {200, 201}:
            fork_data = fork_response.json()
            self.fork_url = fork_data["web_url"]
            logger.info(f"GitLab fork created successfully: {self.fork_url}")
        else:
            logger.error(f"Failed to create GitLab fork: {fork_response.status_code} - {fork_response.text}")
            raise ValueError("Failed to create fork.")

    def star_repository(self) -> None:
        if not self.token:
            raise ValueError("GitLab token is required to star the repository.")

        gitlab_instance = re.match(r"(https?://[^/]*gitlab[^/]*)", self.repo_url).group(1)
        base_repo = get_base_repo_url(self.repo_url)
        project_path = base_repo.replace("/", "%2F")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

        url = f"{gitlab_instance}/api/v4/projects/{project_path}/star"
        response = requests.post(url, headers=headers)

        if response.status_code == 304:
            logger.info(f"GitLab repository '{base_repo}' is already starred.")
            return
        elif response.status_code == 201:
            logger.info(f"GitLab repository '{base_repo}' has been starred successfully.")
            return
        else:
            logger.error(f"Failed to star GitLab repository: {response.status_code} - {response.text}")

    def create_pull_request(self, title: str = None, body: str = None) -> None:
        if not self.token:
            raise ValueError("GitLab token is required to create a merge request.")

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        gitlab_instance = re.match(r"(https?://[^/]*gitlab[^/]*)", self.repo_url).group(1)
        base_repo = get_base_repo_url(self.repo_url)
        source_project_path = get_base_repo_url(self.fork_url).replace("/", "%2F")
        target_project_path = base_repo.replace("/", "%2F")

        project_url = f"{gitlab_instance}/api/v4/projects/{target_project_path}"
        response = requests.get(project_url, headers=headers)
        if response.status_code == 200:
            project_info = response.json()
            target_project_id = project_info["id"]
        else:
            raise ValueError(f"Failed to get project info: {response.status_code} - {response.text}")

        last_commit = self.repo.head.commit
        mr_title = title if title else last_commit.message
        mr_body = body if body else last_commit.message
        mr_body += self.pr_report_body
        mr_body += self.AGENT_SIGNATURE

        mr_data = {
            "title": mr_title,
            "source_branch": self.branch_name,
            "target_branch": self.base_branch,
            "target_project_id": target_project_id,
            "description": mr_body,
            "allow_collaboration": True,
        }

        url = f"{gitlab_instance}/api/v4/projects/{source_project_path}/merge_requests"
        response = requests.post(url, json=mr_data, headers=headers)
        if response.status_code == 201:
            logger.info(f"GitLab merge request created successfully: {response.json()['web_url']}")
        else:
            logger.error(f"Failed to create merge request: {response.status_code} - {response.text}")
            if "merge request already exists" not in response.text:
                raise ValueError("Failed to create merge request.")

    def _update_about_section(self, repo_path: str, about_content: dict) -> None:
        gitlab_instance = re.match(r"(https?://[^/]*gitlab[^/]*)", self.repo_url).group(1)
        project_path = repo_path.replace("/", "%2F")

        url = f"{gitlab_instance}/api/v4/projects/{project_path}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        about_data = {
            "description": about_content["description"],
            "tag_list": about_content["topics"],
        }
        response = requests.put(url, headers=headers, json=about_data)
        if response.status_code in {200, 201}:
            logger.info(f"Successfully updated GitLab repository description and topics.")
        else:
            logger.error(f"{response.status_code} - Failed to update GitLab repository metadata.")

    def _build_report_url(self, report_branch: str, report_filename: str) -> str:
        return f"{self.fork_url}/-/blob/{report_branch}/{report_filename}"

    def _build_auth_url(self, repo_url: str) -> str:
        gitlab_match = re.match(r"https?://([^/]*gitlab[^/]*)/(.+)", repo_url)
        if gitlab_match:
            gitlab_host = gitlab_match.group(1)
            repo_path = gitlab_match.group(2)
            return f"https://oauth2:{self.token}@{gitlab_host}/{repo_path}.git"
        raise ValueError(f"Unsupported repository URL format for GitLab: {repo_url}")

    def validate_topics(self, topics: List[str]) -> List[str]:
        logger.info("Validating topics against GitLab Topics API...")
        validated_topics = []
        base_url = "https://gitlab.com/api/v4/topics"
        headers = {"Accept": "application/json"}

        for topic in topics:
            try:
                params = {"search": topic}
                response = requests.get(base_url, headers=headers, params=params)
                if response.status_code == 200:
                    data = response.json()
                    for entry in data:
                        if entry.get("name") == topic:
                            validated_topics.append(topic)
                            logger.debug(f"Validated GitLab topic: {topic}")
                            break
                    else:
                        logger.debug(f"Topic '{topic}' not found on GitLab, skipping")
                elif response.status_code == 403:
                    logger.warning("Rate limit exceeded, waiting 60 seconds")
                    time.sleep(60)
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error validating topic '{topic}': {e}")
                continue

        logger.info(f"Validated {len(validated_topics)} topics out of {len(topics)}.")
        return validated_topics


class GitverseAgent(GitAgent):
    def _get_token(self) -> str:
        return os.getenv("GITVERSE_TOKEN", os.getenv("GIT_TOKEN", ""))

    def _load_metadata(self, repo_url: str) -> RepositoryMetadata:
        return GitverseMetadataLoader.load_data(repo_url)

    def create_fork(self) -> None:
        if not self.token:
            raise ValueError("Gitverse token is required to create a fork.")

        base_repo = get_base_repo_url(self.repo_url)
        body = {
            "name": f"{self.metadata.name}",
            "description": "osa fork",
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.gitverse.object+json;version=1",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        user_url = "https://api.gitverse.ru/user"
        user_response = requests.get(user_url, headers=headers)
        if user_response.status_code != 200:
            logger.error(f"Failed to get user info: {user_response.status_code} - {user_response.text}")
            raise ValueError("Failed to get user information.")
        current_login = user_response.json().get("login", "")

        if current_login == self.metadata.owner:
            self.fork_url = self.repo_url
            logger.info(f"User '{current_login}' already owns the repository. Using original URL: {self.fork_url}")
            return

        fork_check_url = f"https://api.gitverse.ru/repos/{current_login}/{self.metadata.name}"
        fork_check_response = requests.get(fork_check_url, headers=headers)
        if fork_check_response.status_code == 200:
            fork_data = fork_check_response.json()
            if fork_data.get("fork") and fork_data.get("parent", {}).get("full_name") == base_repo:
                self.fork_url = f'https://gitverse.ru/{fork_data["full_name"]}'
                logger.info(f"Fork already exists: {self.fork_url}")
                return

        fork_url = f"https://api.gitverse.ru/repos/{base_repo}/forks"
        fork_response = requests.post(fork_url, json=body, headers=headers)
        if fork_response.status_code in {200, 201}:
            self.fork_url = "https://gitverse.ru/" + fork_response.json()["full_name"]
            logger.info(f"Gitverse fork created successfully: {self.fork_url}")
        else:
            logger.error(f"Failed to create Gitverse fork: {fork_response.status_code} - {fork_response.text}")
            raise ValueError("Failed to create fork.")

    def star_repository(self) -> None:
        if not self.token:
            raise ValueError("Gitverse token is required to star the repository.")

        base_repo = get_base_repo_url(self.repo_url)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.gitverse.object+json;version=1",
            "User-Agent": "Mozilla/5.0",
        }
        url = f"https://api.gitverse.ru/user/starred/{base_repo}"
        response_check = requests.get(url, headers=headers)
        if response_check.status_code == 204:
            logger.info(f"Gitverse repository '{base_repo}' is already starred.")
            return
        elif response_check.status_code != 404:
            logger.error(f"Failed to check star status: {response_check.status_code} - {response_check.text}")
            raise ValueError("Failed to check star status.")

        response_star = requests.put(url, headers=headers)
        if response_star.status_code == 204:
            logger.info(f"Gitverse repository '{base_repo}' has been starred successfully.")
        else:
            logger.error(f"Failed to star Gitverse repository: {response_star.status_code} - {response_star.text}")

    def create_pull_request(self, title: str = None, body: str = None) -> None:
        if not self.token:
            raise ValueError("Gitverse token is required to create a pull request.")

        base_repo = get_base_repo_url(self.repo_url)
        last_commit = self.repo.head.commit
        pr_title = title if title else last_commit.message
        pr_body = body if body else last_commit.message
        pr_body += self.pr_report_body
        pr_body += self.AGENT_SIGNATURE

        pr_data = {
            "title": pr_title,
            "head": self.branch_name,
            "base": self.base_branch,
            "body": pr_body,
        }
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.gitverse.object+json;version=1",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }
        url = f"https://api.gitverse.ru/repos/{base_repo}/pulls"
        response = requests.post(url, json=pr_data, headers=headers)
        if response.status_code == 201:
            logger.info(f"Gitverse pull request created successfully: {response.json()['html_url']}")
        else:
            logger.error(f"Failed to create pull request: {response.status_code} - {response.text}")
            if "pull request already exists" not in response.text:
                raise ValueError("Failed to create pull request.")

    def _update_about_section(self, repo_path: str, about_content: dict) -> None:
        logger.warning(
            "Updating repository 'About' section via API is not yet supported for Gitverse. You can see suggestions in PR."
        )

    def _build_report_url(self, report_branch: str, report_filename: str) -> str:
        return f"{self.fork_url}/content/{report_branch}/{report_filename}"

    def _build_auth_url(self, repo_url: str) -> str:
        if repo_url.startswith("https://gitverse.ru/"):
            repo_path = repo_url[len("https://gitverse.ru/") :]
            return f"https://{self.token}@gitverse.ru/{repo_path}.git"
        raise ValueError(f"Unsupported repository URL format for Gitverse: {repo_url}")

    def validate_topics(self, topics: List[str]) -> List[str]:
        logger.warning("Topic validation is not yet implemented for Gitverse. Returning original topics list.")
        return topics
