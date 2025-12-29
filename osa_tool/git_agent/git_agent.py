import abc
import os
import re
import time
from typing import List

import requests
from dotenv import load_dotenv
from git import GitCommandError, InvalidGitRepositoryError, Repo

from osa_tool.analytics.metadata import (
    GitHubMetadataLoader,
    GitLabMetadataLoader,
    GitverseMetadataLoader,
    RepositoryMetadata,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import get_base_repo_url, parse_folder_name


class GitAgent(abc.ABC):
    """Abstract base class for Git platform agents.

    This class provides functionality to clone repositories, create and checkout branches,
    commit and push changes, and create pull requests.

    Attributes:
        agent_signature: A signature string appended to a pull request descriptions.
        author: An author name that appended to a pull request description.
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

    def __init__(self, repo_url: str, repo_branch_name: str = None, branch_name: str = "osa_tool", author: str = None):
        """Initializes the agent with repository info.

        Args:
            repo_url: The URL of the GitHub repository.
            repo_branch_name: The name of the repository's branch to be checked out.
            branch_name: The name of the branch to be created. Defaults to "osa_tool".
            author: The name of the author of the pull request.
        """
        load_dotenv()
        self.author = author
        self.repo_url = repo_url
        self.clone_dir = os.path.join(os.getcwd(), parse_folder_name(repo_url))
        self.branch_name = branch_name
        self.repo = None
        self.token = self._get_token()
        self.fork_url = None
        self.metadata = self._load_metadata(self.repo_url)
        self.base_branch = repo_branch_name or self.metadata.default_branch
        self.pr_report_body = ""

    @property
    def agent_signature(self) -> str:
        signature = "\n\n---"
        if self.author:
            signature += f"\n*Author: {self.author}.*"
        signature += (
            "\n*This PR was created by [osa_tool](https://github.com/aimclub/OSA).*"
            "\n_OSA just makes your open source project better!_"
        )
        return signature

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

    def _handle_git_error(self, error: GitCommandError, action: str, raise_exception: bool = True) -> None:
        """
        Parses Git command errors and logs specific messages for 401, 403, 404, 429.

        Args:
            error (GitCommandError): The exception object caught from a failed GitPython operation.
            action (str): A human-readable description of the operation being performed for logging.
            raise_exception (bool): A flag which indicates whether to raise an exception or not.

        Raises:
            Exception: Re-raises a generic Exception chained with the original error.
        """
        stderr = (error.stderr or "").lower()

        # 401/403: Auth/Permission error
        # вроде все пойманные мной сообщения включил
        if (
                "authentication failed" in stderr
                or "could not read username" in stderr
                or "access denied" in stderr
                or "permission denied" in stderr
                or "unable to access" in stderr
                or "403" in stderr
                or "401" in stderr
        ):
            logger.error(f"Auth/Permission Error during {action}.")
            logger.error(f"Details: {stderr}")
            logger.error("Possible reasons:")
            logger.error("1. Invalid GIT_TOKEN (expired or wrong).")
            logger.error("2. Token missing scopes (needs 'repo', 'workflow', 'read:org').")
            logger.error("3. You don't have write access to this repository.")

        # 404: Not found
        elif "not found" in stderr or "404" in stderr:
            logger.error(f"Not Found Error during {action}.")
            logger.error(f"Details: {stderr}")
            logger.error("Possible reasons:")
            logger.error("1. Repository URL is incorrect.")
            logger.error("2. Repository is Private, and your token lacks access.")

        # 429: Rate Limit
        elif "too many requests" in stderr or "abuse detection mechanism" in stderr or "429" in stderr:
            logger.error(f"Rate Limit Exceeded during {action}.")
            logger.error("GitHub has temporarily blocked requests from your IP/Token.")
            logger.error("Please wait a few minutes before retrying.")

        # Ошибка ветки
        elif "remote branch" in stderr:
            logger.error(f"Branch Error: The target branch does not exist in remote.")

        else:
            logger.error(f"Unexpected Git error during {action}: {stderr}")

        if raise_exception:
            raise Exception(f"Git operation '{action}' failed.") from error
        else:
            logger.warning(f"Non-critical error during '{action}'. Continuing execution.")

    def _handle_api_error(self, response: requests.Response, action: str, raise_exception: bool = True) -> None:
        """
        Parses HTTP API errors and logs specific messages for 401, 403, 404, 429.
        Should be called when response.status_code is not 200/201/204.

        Args:
            response (requests.Response): The response object from requests.
            action (str): Description of the action.
            raise_exception (bool): A flag which indicates whether to raise an exception or not.

        Raises:
            Exception: Re-raises a generic Exception chained with the original error.
        """
        code = response.status_code
        try:
            error_json = response.json()
            error_msg = error_json.get("message", response.text)
        except ValueError:
            error_msg = response.text

        logger.error(f"API Request failed during {action}. Status: {code}")
        logger.debug(f"Raw API response: {error_msg}")

        if code == 401:
            logger.error(f"Unauthorized (401). Check your GIT_TOKEN. Message: {error_msg}")
        elif code == 403:
            if "rate limit" in str(error_msg).lower():
                logger.error("API Rate Limit Exceeded (403).")
            else:
                logger.error(f"Forbidden (403). Permissions issue. Message: {error_msg}")
        elif code == 404:
            logger.error(f"Not Found (404). Check URL/ID or Token permissions. Message: {error_msg}")
        elif code == 429:
            logger.error("Too Many Requests (429). You are being rate-limited.")
            if "Retry-After" in response.headers:
                logger.error(f"Retry after: {response.headers['Retry-After']} seconds.")

        if raise_exception:
            raise ValueError(f"API operation '{action}' failed with status {code}.")
        else:
            logger.warning(f"Non-critical API error during '{action}' (Status {code}). Continuing execution.")

    def _check_branch_existence(self, branch: str = "osa_tool") -> bool:
        """
        Checks if a branch exists in the remote repository using platform-specific APIs.

        This method attempts to determine whether the specified branch exists in the
        remote repository before attempting to clone it. It uses different API endpoints
        depending on the Git platform (GitHub, GitLab, or Gitverse).

        Args:
            branch: The name of the branch to check. If None, uses the default branch name
                    configured for this agent (typically "osa_tool").

        Returns:
            True if the branch exists in the remote repository, False otherwise.
            False and logs a warning if the platform is not recognized.
        """
        if branch is None:
            branch = self.branch_name

        if "github.com" in self.repo_url:
            return self._check_github_branch_exists(branch)
        elif "gitlab." in self.repo_url:
            return self._check_gitlab_branch_exists(branch)
        elif "gitverse.ru" in self.repo_url:
            return self._check_gitverse_branch_exists(branch)

        logger.warning(f"Cannot check branch existence for platform: {self.repo_url}")
        return False

    def _clone_chosen_branch(self, branch: str = "osa_tool") -> None:
        """Clones an existing branch from the remote repository.

        Args:
            branch: The name of the branch to clone. Defaults to `branch_name`.

        Returns:
            True if cloning was successful, False otherwise.
        """
        if branch is None:
            branch = self.branch_name

        try:
            logger.info(f"Cloning existing branch '{branch}' from {self.fork_url or self.repo_url}...")
            self.repo = Repo.clone_from(
                url=self._get_auth_url(self.fork_url or self.repo_url),
                to_path=self.clone_dir,
                branch=branch,
                single_branch=True,
            )
            logger.info(f"Successfully cloned branch '{branch}'")
        except GitCommandError as e:
            self._handle_git_error(e, f"cloning branch '{branch}'")
        except Exception as e:
            raise Exception(f"Failed to clone branch '{branch}': {e}") from e

    def _clone_default_branch(self) -> None:
        """
        Clones the default branch of the repository.

        This method implements the standard cloning logic with fallback mechanisms:
        1. First attempts unauthenticated cloning (for public repositories)
        2. Falls back to authenticated cloning if unauthenticated fails
        3. Provides detailed error messages for common Git errors

        Raises:
            GitCommandError: If both cloning attempts fail with Git-specific errors.
            Exception: If an unexpected error occurs during cloning.

        Note:
            The 'single_branch=True' parameter is used to clone only the requested
            branch, which is more efficient than cloning all branches.
        """
        try:
            logger.info(
                f"Cloning the '{self.base_branch}' branch from {self.repo_url} into directory {self.clone_dir}..."
            )

            # First attempt: unauthenticated cloning (works for public repos)
            self.repo = Repo.clone_from(
                url=self._get_unauth_url(),
                to_path=self.clone_dir,
                branch=self.base_branch,
                single_branch=True,
            )
            logger.info("Cloning completed")

        except Exception as e:
            # Second attempt: authenticated cloning (for private repos or rate limits)
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
                self._handle_git_error(e, f"cloning repository ({self.repo_url})")
            except Exception as e:
                raise Exception(f"Unexpected error during cloning: {e}")

    def clone_repository(self) -> None:
        """
        Clones or initializes the Git repository in the local filesystem.

        This is the main entry point for obtaining a local copy of the repository.
        It implements a multi-step strategy:
        1. If the repository is already initialized, returns early.
        2. If the directory exists locally, initializes from existing files.
        3. If cloning is needed, checks for existing 'osa_tool' branch first.
        4. Falls back to cloning the default branch if 'osa_tool' doesn't exist.

        Raises:
            InvalidGitRepositoryError: If the local directory exists but is not a valid Git repository.
            Exception: If all cloning attempts fail.

        Note:
            This method handles both authenticated and unauthenticated cloning attempts
            for the default branch. It prefers the fork URL when available.
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

        elif self._check_branch_existence():
            self._clone_chosen_branch()
        else:
            self._clone_default_branch()

    def get_attachment_branch_files(self, branch: str = "osa_tool_attachments") -> List[str]:
        """Gets list of report files from attachment branch.

        Args:
            branch: The name of the attachment branch.

        Returns:
            List of report filenames found in the branch.
        """
        try:
            remote_refs = self.repo.git.ls_remote("--heads", self._get_unauth_url(self.fork_url or self.repo_url))

            if f"refs/heads/{branch}" not in remote_refs:
                return []

            self.repo.git.fetch("origin", f"{branch}:{branch}_tmp", depth=1)

            files_output = self.repo.git.ls_tree("-r", "--name-only", f"{branch}_tmp")
            report_files = [f for f in files_output.split("\n") if f and f.endswith("report.pdf")]

            self.repo.git.branch("-D", f"{branch}_tmp")

            logger.debug(f"Found {len(report_files)} report files in branch '{branch}'")
            return report_files
        except Exception as e:
            logger.warning(f"Failed to get files from attachment branch: {e}")
            return []

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
                self._handle_git_error(e, "git commit")

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
            stderr = (e.stderr or "").lower()
            if any(x in stderr for x in ["403", "401", "404", "auth", "denied", "unable to access"]):
                self._handle_git_error(e, f"pushing to {branch}")
            # если ни одна из ошибок не покрыла наш кейс - старая логика
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
        report_link = f"\nGenerated report - [{report_filename}]({report_url})\n"
        self.pr_report_body += report_link

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
            self._handle_api_error(response, "creating GitHub fork")

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
            self._handle_api_error(response_check, "checking star status", raise_exception=False)

        response_star = requests.put(url, headers=headers)
        if response_star.status_code == 204:
            logger.info(f"GitHub repository '{base_repo}' has been starred successfully.")
        else:
            self._handle_api_error(response_star, "starring repository", raise_exception=False)

    def _check_github_branch_exists(self, branch: str) -> bool:
        """Check if branch exists on GitHub using API."""
        if not self.fork_url:
            repo_to_check = get_base_repo_url(self.repo_url)
            url = f"https://api.github.com/repos/{repo_to_check}/branches/{branch}"
        else:
            repo_to_check = get_base_repo_url(self.fork_url)
            url = f"https://api.github.com/repos/{repo_to_check}/branches/{branch}"

        headers = {
            "Accept": "application/vnd.github.v3+json",
        }

        if self.token:
            headers["Authorization"] = f"token {self.token}"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
            else:
                logger.warning(f"GitHub API returned {response.status_code} for branch check")
                return False
        except Exception as e:
            logger.warning(f"Failed to check GitHub branch: {e}")
            return False

    def post_comment(self, pr_number: int, comment_body: str):
        base_repo = get_base_repo_url(self.repo_url)
        url = f"https://api.github.com/repos/{base_repo}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        data = {"body": comment_body}
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            logger.info(f"Successfully posted a comment to PR #{pr_number}.")
        else:
            logger.error(f"Failed to post a comment to PR #{pr_number}: {response.status_code} - {response.text}")

    def create_pull_request(self, title: str = None, body: str = None, changes: bool = False) -> None:
        """Creates or updates a pull request on GitHub.

        This method implements intelligent PR management:
        1. Checks if an open PR already exists for the current branch
        2. If PR exists and there are new reports, updates the PR description
           with all unique report links (removing duplicates)
        3. If no PR exists, creates a new one with all available reports
           from the attachment branch

        Args:
            title: Optional title for the PR. Uses last commit message if not provided.
            body: Optional body/description for the PR.
        """
        if not self.token:
            raise ValueError("GIT_TOKEN or GITHUB_TOKEN token is required to create a pull request.")

        base_repo = get_base_repo_url(self.repo_url)
        head_branch = f"{self.fork_url.split('/')[-2]}:{self.branch_name}"

        url = f"https://api.github.com/repos/{base_repo}/pulls"
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

        last_commit = self.repo.head.commit
        pr_title = title if title else last_commit.message

        params = {"state": "open", "head": head_branch, "base": self.base_branch}
        response = requests.get(url, headers=headers, params=params)

        if response.status_code != 200:
            # не смогли получить список PR - ошибка прав или сети
            self._handle_api_error(response, "checking existing pull requests", False)

        prs = response.json() if response.status_code == 200 else []
        if prs:
            existing_pr = prs[0]
            pr_number = existing_pr["number"]
            logger.info(f"Pull request #{pr_number} already exists.")

            if body and body.strip():
                self.post_comment(pr_number, body)

            if self.pr_report_body.strip():
                old_pr_body = existing_pr.get("body", "") or ""

                report_pattern = re.compile(r"Generated report - \[.*?\]\(.*?\)")
                old_reports = report_pattern.findall(old_pr_body)
                new_reports = report_pattern.findall(self.pr_report_body)
                all_reports = sorted(list(set(old_reports + new_reports)))

                clean_body = report_pattern.sub("", old_pr_body).replace(self.AGENT_SIGNATURE, "").strip()

                updated_body = clean_body
                if all_reports:
                    updated_body += "\n\n" + "\n".join(all_reports)
                updated_body += self.AGENT_SIGNATURE

                update_url = f"{url}/{pr_number}"
                update_data = {"body": updated_body.strip()}

                update_response = requests.patch(update_url, json=update_data, headers=headers)
                if update_response.status_code == 200:
                    logger.info(f"Successfully updated PR #{pr_number} with new reports.")
                else:
                    self._handle_api_error(update_response, f"updating PR #{pr_number}", raise_exception=False)
        elif changes:
            report_files = self.get_attachment_branch_files()
            report_branch = "osa_tool_attachments"
            for report_file in report_files:
                report_url = self._build_report_url(report_branch, report_file)
                report_link = f"\nGenerated report - [{report_file}]({report_url})\n"
                if report_link not in self.pr_report_body:
                    self.pr_report_body += report_link

            content_for_publish = (body if body else "") + self.pr_report_body
            pr_body = content_for_publish + self.agent_signature

            pr_data = {
                "title": pr_title,
                "head": head_branch,
                "base": self.base_branch,
                "body": pr_body,
                "maintainer_can_modify": True,
            }

            response = requests.post(url, json=pr_data, headers=headers)
            if response.status_code == 201:
                logger.info(f"GitHub pull request created successfully: {response.json()['html_url']}")
            else:
                self._handle_api_error(response, "creating pull request", raise_exception=True)

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
            self._handle_api_error(response, f"updating description for '{repo_path}'", raise_exception=False)

        url = f"https://api.github.com/repos/{repo_path}/topics"
        topics_data = {"names": about_content["topics"]}
        response = requests.put(url, headers=headers, json=topics_data)
        if response.status_code in {200, 201}:
            logger.info(f"Successfully updated GitHub repository topics for '{repo_path}'")
        else:
            self._handle_api_error(response, f"updating topics for '{repo_path}'", raise_exception=False)

    def _build_report_url(self, report_branch: str, report_filename: str) -> str:
        return f"{self.fork_url}/blob/{report_branch}/{report_filename}"

    def _build_auth_url(self, repo_url: str) -> str:
        if repo_url.startswith("https://github.com/"):
            repo_path = repo_url[len("https://github.com/"):]
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

        user_data = user_response.json()
        current_user_id = user_data.get("id")
        current_username = user_data.get("username")

        project_url = f"{gitlab_instance}/api/v4/projects/{project_path}"
        project_response = requests.get(project_url, headers=headers)
        if project_response.status_code != 200:
            logger.warning(
                f"Could not fetch project details to verify owner. Proceeding with fork logic. Status: {project_response.status_code}"
            )
        else:
            project_data = project_response.json()
            owner_id = project_data.get("owner", {}).get("id")

            if current_user_id and owner_id and current_user_id == owner_id:
                self.fork_url = self.repo_url
                logger.info(
                    f"User (ID: {current_user_id}) already owns the repository. Using original URL: {self.fork_url}"
                )
                return

        forks_url = f"{gitlab_instance}/api/v4/projects/{project_path}/forks"
        forks_response = requests.get(forks_url, headers=headers)
        if forks_response.status_code != 200:
            logger.error(f"Failed to get forks: {forks_response.status_code} - {forks_response.text}")
            raise ValueError("Failed to get forks list.")

        forks = forks_response.json()
        for fork in forks:
            namespace = fork.get("namespace", {})
            fork_owner_username = namespace.get("path") or namespace.get("name") or ""
            if fork_owner_username == current_username:
                self.fork_url = fork["web_url"]
                logger.info(f"Fork already exists: {self.fork_url}")
                return

        fork_url = f"{gitlab_instance}/api/v4/projects/{project_path}/fork"
        fork_response = requests.post(fork_url, headers=headers)
        if fork_response.status_code in {200, 201, 202}:
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

    def _check_gitlab_branch_exists(self, branch: str) -> bool:
        """Check if branch exists on GitLab using API."""
        gitlab_instance = re.match(r"(https?://[^/]*gitlab[^/]*)", self.repo_url).group(1)

        if not self.fork_url:
            repo_to_check = get_base_repo_url(self.repo_url)
        else:
            repo_to_check = get_base_repo_url(self.fork_url)

        project_path = repo_to_check.replace("/", "%2F")
        url = f"{gitlab_instance}/api/v4/projects/{project_path}/repository/branches/{branch}"

        headers = {
            "Accept": "application/json",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                return True
            elif response.status_code == 404:
                return False
            else:
                logger.warning(f"GitLab API returned {response.status_code} for branch check")
                return False
        except Exception as e:
            logger.warning(f"Failed to check GitLab branch: {e}")
            return False

    def post_note(self, project_id: int, mr_iid: int, note_body: str):
        gitlab_instance = re.match(r"(https?://[^/]*gitlab[^/]*)", self.repo_url).group(1)
        url = f"{gitlab_instance}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        data = {"body": note_body}
        response = requests.post(url, json=data, headers=headers)
        if response.status_code == 201:
            logger.info(f"Successfully posted a note to MR !{mr_iid}.")
        else:
            logger.error(f"Failed to post a note to MR !{mr_iid}: {response.status_code} - {response.text}")

    def create_pull_request(self, title: str = None, body: str = None, changes: bool = False) -> None:
        """Creates or updates a merge request on GitLab.

        This method implements intelligent MR management:
        1. Checks if an open MR already exists for the current branch
        2. If MR exists and there are new reports, updates the MR description
           with all unique report links (removing duplicates)
        3. If no MR exists, creates a new one with all available reports
           from the attachment branch

        Args:
            title: Optional title for the MR. Uses last commit message if not provided.
            body: Optional body/description for the MR.
            changes: Flag indicating whether there are changes to commit.
        """
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
        proj_response = requests.get(project_url, headers=headers)
        if proj_response.status_code != 200:
            raise ValueError(f"Failed to get project info: {proj_response.status_code} - {proj_response.text}")
        target_project_id = proj_response.json()["id"]

        last_commit = self.repo.head.commit
        mr_title = title if title else last_commit.message
        new_body_content = (body if body else "").strip()

        mr_url = f"{gitlab_instance}/api/v4/projects/{source_project_path}/merge_requests"
        params = {
            "state": "opened",
            "source_branch": self.branch_name,
            "target_branch": self.base_branch,
            "target_project_id": target_project_id,
        }
        response = requests.get(mr_url, headers=headers, params=params)
        mrs = response.json() if response.status_code == 200 else []

        if mrs:
            existing_mr = mrs[0]
            mr_iid = existing_mr.get("iid") or existing_mr.get("id")
            logger.info(f"Merge request !{mr_iid} already exists.")

            if new_body_content:
                self.post_note(target_project_id, mr_iid, new_body_content)

            if self.pr_report_body.strip():
                old_mr_body = existing_mr.get("description", "") or ""

                report_pattern = re.compile(r"Generated report - \[.*?\]\(.*?\)")
                old_reports = report_pattern.findall(old_mr_body)
                new_reports = report_pattern.findall(self.pr_report_body)
                all_reports = sorted(list(set(old_reports + new_reports)))

                clean_body = report_pattern.sub("", old_mr_body).replace(self.AGENT_SIGNATURE, "").strip()

                updated_body = clean_body
                if all_reports:
                    updated_body += "\n\n" + "\n".join(all_reports)
                updated_body += self.AGENT_SIGNATURE

                update_url = f"{gitlab_instance}/api/v4/projects/{target_project_id}/merge_requests/{mr_iid}"
                update_data = {"description": updated_body.strip()}

                update_response = requests.put(update_url, json=update_data, headers=headers)
                if update_response.status_code == 200:
                    logger.info(f"Successfully updated MR !{mr_iid} with new reports.")
                else:
                    logger.error(
                        f"Failed to update MR !{mr_iid} description: {update_response.status_code} - {update_response.text}"
                    )
        elif changes:
            report_files = self.get_attachment_branch_files()
            report_branch = "osa_tool_attachments"
            for report_file in report_files:
                report_url = self._build_report_url(report_branch, report_file)
                report_link = f"\nGenerated report - [{report_file}]({report_url})\n"
                if report_link not in self.pr_report_body:
                    self.pr_report_body += report_link

            content_for_publish = new_body_content + self.pr_report_body
            mr_body = content_for_publish + self.agent_signature

            mr_data = {
                "title": mr_title,
                "source_branch": self.branch_name,
                "target_branch": self.base_branch,
                "target_project_id": target_project_id,
                "description": mr_body,
                "allow_collaboration": True,
            }

            response = requests.post(mr_url, json=mr_data, headers=headers)
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

    def _check_gitverse_branch_exists(self, branch: str) -> bool:
        """Check if branch exists on Gitverse using API."""
        if not self.fork_url:
            repo_to_check = get_base_repo_url(self.repo_url)
        else:
            repo_to_check = get_base_repo_url(self.fork_url)

        url = f"https://api.gitverse.ru/repos/{repo_to_check}/branches"

        headers = {
            "Accept": "application/vnd.gitverse.object+json;version=1",
            "User-Agent": "Mozilla/5.0",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                branches = response.json()
                return any(b.get("name") == branch for b in branches)
            else:
                logger.warning(f"Gitverse API returned {response.status_code} for branch check")
                return False
        except Exception as e:
            logger.warning(f"Failed to check Gitverse branch: {e}")
            return False

    def create_pull_request(self, title: str = None, body: str = None, changes: bool = False) -> None:
        """Creates or updates a pull request on Gitverse.

        This method implements intelligent PR management:
        1. Checks if an open PR already exists for the current branch
        2. If PR exists and there are new reports, updates the PR description
           with all unique report links (removing duplicates)
        3. If no PR exists, creates a new one with all available reports
           from the attachment branch

        Args:
            title: Optional title for the PR. Uses last commit message if not provided.
            body: Optional body/description for the PR.
            changes: Flag indicating whether there are changes to commit.
        """
        if not self.token:
            raise ValueError("Gitverse token is required to create a pull request.")

        base_repo = get_base_repo_url(self.repo_url)
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.gitverse.object+json;version=1",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        }

        url = f"https://api.gitverse.ru/repos/{base_repo}/pulls"
        last_commit = self.repo.head.commit
        pr_title = title if title else last_commit.message
        new_body_content = (body or "").strip()

        report_pattern = re.compile(r"Generated report - \[.*?\]\(.*?\)")

        def extract_reports(text: str) -> list[str]:
            return report_pattern.findall(text or "")

        def strip_signature(text: str) -> str:
            return (text or "").replace(self.agent_signature, "").strip()

        def remove_reports(text: str) -> str:
            return report_pattern.sub("", text or "").strip()

        def uniq_keep_order(items: list[str]) -> list[str]:
            seen = set()
            out = []
            for x in items:
                if x not in seen:
                    seen.add(x)
                    out.append(x)
            return out

        def build_body(initial_and_history: str, reports: list[str]) -> str:
            parts = []
            if initial_and_history.strip():
                parts.append(initial_and_history.strip())
            if reports:
                parts.append("\n".join(reports).strip())
            return "\n\n".join(parts).strip() + self.AGENT_SIGNATURE

        params = {"state": "open", "head": self.branch_name, "base": self.base_branch}
        response = requests.get(url, headers=headers, params=params)
        prs = response.json() if response.status_code == 200 else []

        if prs:
            existing_pr = prs[0]
            pr_number = existing_pr.get("number")
            pr_url = f"https://gitverse.ru/{base_repo}/pulls/{pr_number}"
            logger.info(f"Pull request already exists. Updating PR #{pr_number}: {pr_url}")

            old_body = existing_pr.get("body", "") or ""

            clean_text = remove_reports(strip_signature(old_body))

            all_reports = uniq_keep_order(extract_reports(old_body) + extract_reports(self.pr_report_body))

            if new_body_content and new_body_content not in clean_text:
                clean_text = (clean_text + "\n\n" + new_body_content).strip()

            updated_body = build_body(clean_text, all_reports)

            update_url = f"{url}/{pr_number}"
            update_data = {"title": pr_title, "body": updated_body}
            update_response = requests.patch(update_url, json=update_data, headers=headers)

            if update_response.status_code == 200:
                logger.info(f"Pull request #{pr_number} updated successfully.")
            else:
                logger.error(f"Failed to update pull request: {update_response.status_code} - {update_response.text}")

        elif changes:
            report_files = self.get_attachment_branch_files()
            report_branch = "osa_tool_attachments"
            for report_file in report_files:
                report_url = self._build_report_url(report_branch, report_file)
                report_link = f"\nGenerated report - [{report_file}]({report_url})\n"
                if report_link not in self.pr_report_body:
                    self.pr_report_body += report_link

            reports = uniq_keep_order(extract_reports(self.pr_report_body))
            pr_body = build_body(new_body_content, reports)

            pr_data = {"title": pr_title, "head": self.branch_name, "base": self.base_branch, "body": pr_body}
            response = requests.post(url, json=pr_data, headers=headers)

            if response.status_code == 201:
                pr_number = response.json()["number"]
                pr_url = f"https://gitverse.ru/{base_repo}/pulls/{pr_number}"
                logger.info(f"Gitverse pull request created successfully: {pr_url}")
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
            repo_path = repo_url[len("https://gitverse.ru/"):]
            return f"https://{self.token}@gitverse.ru/{repo_path}.git"
        raise ValueError(f"Unsupported repository URL format for Gitverse: {repo_url}")

    def validate_topics(self, topics: List[str]) -> List[str]:
        logger.warning("Topic validation is not yet implemented for Gitverse. Returning original topics list.")
        return topics
