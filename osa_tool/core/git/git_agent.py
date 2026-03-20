import abc
import os
import re
import time
from typing import List

import requests
from dotenv import load_dotenv
from git import GitCommandError, InvalidGitRepositoryError, Repo

from osa_tool.core.git.metadata import (
    GitHubMetadataLoader,
    GitLabMetadataLoader,
    GitverseMetadataLoader,
    RepositoryMetadata,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import get_base_repo_url, parse_folder_name


class GitAgent(abc.ABC):
    """
    Base class for Git platform integration, handling repository operations and interactions.
    
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
        """
        Initializes the agent with repository information and prepares the environment for operations.
        
        Args:
            repo_url: The URL of the GitHub repository.
            repo_branch_name: The name of the repository's branch to be checked out. If not provided, defaults to the repository's default branch from its metadata.
            branch_name: The name of the new branch to be created for the agent's work. Defaults to "osa_tool".
            author: The name of the author to be associated with generated pull requests.
        
        Why:
        - The agent clones the repository into a local directory derived from the repo_url (using parse_folder_name) to isolate its work.
        - It loads environment variables (like authentication tokens) and repository metadata to enable authenticated API calls and to determine the base branch if repo_branch_name is not specified.
        - The base_branch is set either to the provided repo_branch_name or to the default branch from the repository metadata, ensuring the agent operates on the correct starting point.
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
        """
        Generates a standardized signature string for the agent to be used in PR descriptions.
        This signature provides attribution to the human author (when known) and includes a promotional footer for the OSA tool, enhancing transparency and promoting the automated tool that created the pull request.
        
        Returns:
            A formatted string containing a separator line, the author's name (if available), and a promotional footer for the osa_tool.
        """
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
        """
        Return the platform-specific authentication token from environment variables.
        
        This method retrieves the appropriate token (e.g., for GitHub, GitLab, or Bitbucket) based on the platform the GitAgent is configured to interact with. It is used internally to authenticate API requests without hard‑coding credentials.
        
        Args:
            self: The GitAgent instance.
        
        Returns:
            The token as a string, retrieved from the corresponding environment variable.
        """
        pass

    @abc.abstractmethod
    def _load_metadata(self, repo_url: str) -> RepositoryMetadata:
        """
        Return platform-specific repository metadata for a given Git repository URL.
        
        This method is responsible for extracting or constructing metadata that is specific to the platform hosting the repository (e.g., GitHub, GitLab). The metadata typically includes information such as the repository's owner, name, default branch, visibility, and platform-specific identifiers, which are essential for subsequent operations like cloning, analysis, or documentation generation within the OSA Tool.
        
        Args:
            repo_url: The URL of the Git repository from which to load metadata.
        
        Returns:
            A RepositoryMetadata object containing the structured platform-specific details.
        """
        pass

    @abc.abstractmethod
    def create_fork(self) -> None:
        """
        Create a fork of the repository.
        
        This method is intended to fork the current repository under the authenticated user's account or a specified organization. It is a placeholder for future implementation where the actual fork operation will be performed via the Git provider's API (e.g., GitHub, GitLab).
        
        WHY: Forking is a common prerequisite for contributing to open-source projects, allowing users to make changes in their own copy before submitting a pull request. This method will enable automated repository enhancement workflows within the OSA Tool to operate on a fork rather than the original repository.
        
        Args:
            self: The GitAgent instance representing the current repository context.
        
        Note:
            This method currently does not perform any action and is a stub for future development.
        """
        pass

    @abc.abstractmethod
    def star_repository(self) -> None:
        """
        Star the repository on the platform.
        
        This method is a placeholder for the functionality to star (or bookmark) the current repository on the hosting platform (e.g., GitHub, GitLab). It is intended to be implemented to allow the GitAgent to perform repository starring as part of automated repository enhancement or interaction workflows.
        
        Args:
            None.
        
        Returns:
            None.
        
        Note:
            The current implementation is a stub and does not perform any action. Actual implementation would require platform-specific API integration and authentication.
        """
        pass

    @abc.abstractmethod
    def create_pull_request(self, title: str = None, body: str = None) -> None:
        """
        Create a pull request or merge request on the platform.
        
        This method initiates the creation of a pull request (PR) or merge request (MR) on the connected Git platform (e.g., GitHub, GitLab). It is used to propose changes from the current branch to another branch, typically as part of an automated documentation or enhancement workflow.
        
        Args:
            title: The title of the PR/MR. If None, the commit message of the latest commit will be used.
            body: The body/description of the PR/MR. If None, the commit message appended with the agent's signature will be used.
        
        Why:
            This method enables automated contribution workflows by programmatically creating pull requests, which is essential for tools that generate documentation or apply repository enhancements without manual intervention.
        """
        pass

    @staticmethod
    def _handle_git_error(error: GitCommandError, action: str, raise_exception: bool = True) -> None:
        """
        Parses Git command errors and logs specific messages for 401, 403, 404, 429, and other common error patterns.
        
        This method centralizes error handling for Git operations, providing user-friendly log messages and actionable guidance for common failure scenarios. It distinguishes between critical errors (which halt execution) and non-critical errors (which allow the tool to continue), enabling robust operation in automated workflows.
        
        Args:
            error: The exception object caught from a failed GitPython operation.
            action: A human-readable description of the operation being performed, used for contextual logging.
            raise_exception: A flag which indicates whether to raise an exception after logging. If True, a generic Exception is raised, chained with the original error. If False, only a warning is logged and execution continues.
        
        Raises:
            Exception: Re-raises a generic Exception chained with the original error when `raise_exception` is True. The exception is only raised after the relevant error details have been logged.
        
        Notes:
            - Specific error patterns detected include authentication/permission failures (401, 403), "not found" errors (404), rate limiting (429), and missing remote branches.
            - For each detected pattern, structured error messages and possible remediation steps are logged.
            - When `raise_exception` is False, the method logs a warning and allows the program to continue. This is intended for non-critical operations (e.g., starring a repository, checking for updates) where failure should not stop the primary documentation generation workflow.
        """
        stderr = (error.stderr or "").lower()

        # 401/403: Auth/Permission error
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
            # Doesn't raise an error for Non-critical errors.
            # For example: starring a repository (star_repository), checking for updates, or posting non-essential
            # comments. If these fail due to API limits or lack of scopes, the tool should log a warning but continue
            # the README/documentation generation.
            logger.warning(f"Non-critical error during '{action}'. Continuing execution.")

    @staticmethod
    def _handle_api_error(response: requests.Response, action: str, raise_exception: bool = True) -> None:
        """
        Parses HTTP API errors and logs specific messages for 401, 403, 404, 429.
        Should be called when response.status_code is not 200/201/204.
        
        WHY: This method centralizes error handling for common HTTP error codes, providing
        tailored logging and optional exception raising to streamline API error management.
        
        Args:
            response: The response object from requests.
            action: Description of the action that triggered the API call.
            raise_exception: A flag which indicates whether to raise an exception or not.
                If True, raises a ValueError after logging. If False, logs a warning and continues.
        
        Raises:
            ValueError: If raise_exception is True, raises a ValueError with a summary of the failure.
                The exception is raised after logging the detailed error information.
        
        Notes:
            - For 401 errors, logs a message about unauthorized access, typically due to an invalid GIT_TOKEN.
            - For 403 errors, distinguishes between general forbidden errors and rate limit issues.
            - For 404 errors, logs a message suggesting checks for URL/ID or token permissions.
            - For 429 errors, logs rate-limiting details and includes Retry-After header information if present.
            - For all other error codes, logs generic failure details.
            - The method extracts error messages from the JSON response body if available; otherwise, uses the raw response text.
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
        
        WHY: This pre‑check avoids cloning operations when the target branch does not exist,
        saving time and network resources.
        
        Args:
            branch: The name of the branch to check. If None, the method uses the agent's
                    default branch name (stored in `self.branch_name`). The parameter
                    defaults to "osa_tool" if not provided.
        
        Returns:
            True if the branch exists in the remote repository, False otherwise.
            Returns False and logs a warning if the platform is not recognized.
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
        """
        Clones an existing branch from the remote repository into a local directory.
        
        This method is used to initialize a local working copy of a specific branch from the remote repository, which is necessary for subsequent operations like documentation generation or repository enhancements.
        
        Args:
            branch: The name of the branch to clone. Defaults to "osa_tool". If None is provided, the instance's `branch_name` attribute is used instead.
        
        Raises:
            GitCommandError: If the Git clone operation fails, the error is handled internally by `_handle_git_error`.
            Exception: For any other unexpected errors during the cloning process, an exception is raised with a descriptive message.
        
        Note:
            The clone uses single-branch cloning for efficiency, fetching only the specified branch. The remote URL is determined by `self.fork_url` if available, otherwise `self.repo_url`, and authentication is applied via `_get_auth_url`. The clone destination is `self.clone_dir`.
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
        
        This method implements a two‑step cloning logic with fallback mechanisms:
        1. First attempts unauthenticated cloning (for public repositories)
        2. Falls back to authenticated cloning if unauthenticated fails (for private repositories or when rate‑limited)
        3. Provides detailed error messages for common Git errors
        
        The method clones only the requested branch (single_branch=True) for efficiency.  
        If both cloning attempts fail, a GitCommandError is raised for Git‑specific issues; otherwise, a generic Exception is raised for unexpected errors.
        
        Args:
            self: The GitAgent instance containing the repository URL, clone directory, and base branch.
        
        Raises:
            GitCommandError: If both cloning attempts fail due to Git‑specific errors (e.g., invalid URL, missing permissions).
            Exception: If an unexpected, non‑Git error occurs during cloning.
        
        Note:
            The authenticated URL is obtained via `self._get_auth_url()` and the unauthenticated URL via `self._get_unauth_url()`.
            The clone directory and base branch are taken from instance attributes (`self.clone_dir`, `self.base_branch`).
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
        
        Why this multi-step approach? It ensures efficient repository setup by reusing existing local data when possible and gracefully handling missing branches.
        
        Args:
            self: The GitAgent instance. Uses internal state like repo_url, clone_dir, and repo.
        
        Raises:
            InvalidGitRepositoryError: If the local directory exists but is not a valid Git repository.
            Exception: If all cloning attempts fail.
        
        Note:
            This method handles both authenticated and unauthenticated cloning attempts
            for the default branch. It prefers the fork URL when available.
            The method does not return a value; it initializes the internal `self.repo` attribute.
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
        """
        Gets list of report files from attachment branch.
        
        This method fetches a specific branch (typically used for storing attachments like PDF reports) from the remote repository, lists all files in that branch, and filters for PDF report files. It is used to retrieve externally stored reports without cloning the entire branch history.
        
        Args:
            branch: The name of the attachment branch. Defaults to "osa_tool_attachments".
        
        Returns:
            List of report filenames (ending with "report.pdf") found in the branch. Returns an empty list if the branch does not exist or if an error occurs.
        
        Why:
        - The method checks if the branch exists remotely before fetching to avoid unnecessary operations.
        - It fetches only the latest commit (depth=1) to minimize data transfer.
        - A temporary local branch is created and then deleted to avoid polluting the local repository with attachment branches.
        - Errors are caught and logged, returning an empty list to allow graceful failure in the calling code.
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
        """
        Creates and checks out a new branch.
        
        If the branch already exists, it simply checks out the branch. If it does not exist, a new branch is created and checked out.
        
        Args:
            branch: The name of the branch to create or check out. If not provided, defaults to the instance's `branch_name` attribute.
        
        Why:
            This method ensures a smooth workflow by automatically handling both branch creation and checkout in a single operation, avoiding manual checks for branch existence. It is commonly used when preparing the repository for modifications that should be isolated in a specific branch.
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
        """
        Commits and pushes changes to the forked repository.
        
        This method stages all changes in the working directory, creates a commit, and pushes it to the specified branch in the user's fork. It includes error handling for common Git issues, such as a clean working tree or index corruption, and provides guidance if the target branch already exists remotely.
        
        Args:
            branch: The name of the branch to push changes to. If not provided, defaults to the instance's `branch_name` attribute.
            commit_message: The commit message to use. Defaults to "osa_tool recommendations".
            force: If True, performs a force push. If False (default), uses `--force-with-lease` for safety.
        
        Returns:
            bool: True if the push was successful. False if there was nothing to commit or if the push failed because the branch already exists in the remote fork.
        
        Raises:
            ValueError: If the `fork_url` is not set, indicating a fork has not been created.
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
            stderr = (e.stderr or "").lower()

            if "nothing to commit" in str(e):
                logger.warning("Nothing to commit: working tree clean")
                if self.pr_report_body:
                    logger.info(self.pr_report_body)
                return False
            elif "bad tree object" in stderr or "invalid object" in stderr:
                logger.warning("Git index corruption detected. Attempting to repair and retry...")
                try:
                    self.repo.git.reset()  # reset to staging area
                    self.repo.git.add(".")  # re-indexing all the files again
                    self.repo.git.commit("-m", commit_message)
                    logger.info("Index repaired and changes committed.")
                except GitCommandError as retry_e:
                    # if the reset didn't help
                    self._handle_git_error(retry_e, "git commit repair retry")
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
            self._handle_git_error(e, f"pushing to {branch}")
            logger.error(f"""Push failed: Branch '{branch}' already exists in the fork.
                 To resolve this, please either:
                   1. Choose a different branch name that doesn't exist in the fork 
                      by modifying the `branch_name` parameter.
                   2. Delete the existing branch from forked repository.
                   3. Delete the fork entirely.""")
            return False

    def upload_report(
        self,
        report_filename: str,
        report_filepath: str,
        report_branch: str = "osa_tool_attachments",
        commit_message: str = "docs: upload pdf report",
    ) -> None:
        """
        Uploads the generated PDF report to a separate branch.
        
        This method handles the process of committing and pushing a generated PDF report to a dedicated branch in the repository. It ensures the report is stored separately from the main working branch, provides a publicly accessible URL for the report, and appends a link to the report in the pull request body for easy access.
        
        Args:
            report_filename: Name of the report file.
            report_filepath: Path to the report file on the local system.
            report_branch: Name of the branch for storing reports. Defaults to "osa_tool_attachments".
            commit_message: Commit message for the report upload. Defaults to "docs: upload pdf report".
        
        Why:
            - Storing reports in a separate branch keeps the main working branch clean and organizes attachments distinctly.
            - The method switches back to the original branch after uploading to maintain the expected working state.
            - Appending a markdown link to the pull request body automatically provides visibility and access to the uploaded report.
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
        """
        Returns the URL to the report file on the corresponding platform.
        This URL is constructed using the repository's base URL, the specified branch, and the report filename, enabling direct access to the stored report.
        
        Args:
            report_branch: Name of the branch for storing reports. Defaults to "osa_tool_attachments".
            report_filename: Name of the report file, which will be appended to the branch path in the URL.
        
        Returns:
            The full URL string pointing to the report file on the platform (e.g., GitHub, GitLab).
        """
        pass

    def update_about_section(self, about_content: dict) -> None:
        """
        Tries to update the 'About' section of the base and fork repository with the provided content.
        
        This method ensures that both the original (base) repository and its fork have consistent metadata in their 'About' sections, which typically includes descriptions, website links, and other repository details displayed on the platform.
        
        Args:
            about_content: Dictionary containing the metadata to update the 'About' section. The exact keys and values depend on the Git platform's API requirements.
        
        Raises:
            ValueError: If the Git token is not set, the fork URL is not set, or an inappropriate platform is used. The fork must be created before this method is called.
        
        Why:
            Keeping the 'About' sections synchronized between the base and fork repositories helps maintain consistent project information across both locations, which is important for clarity and proper attribution when working with forked projects.
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
        """
        A platform-specific helper method for updating the About section of a repository.
        This method is intended for use within the GitAgent class to handle platform-specific API calls or operations required to modify the repository's About metadata, such as description, website, or topics.
        
        Args:
            repo_path: The base repository path (e.g., 'username/repo-name').
            about_content: Dictionary containing the metadata to update the About section. The exact keys and values depend on the platform's API requirements.
        
        Why:
            The About section on platforms like GitHub or GitLab provides a summary and links for the repository. This method centralizes the update logic to accommodate differences between platforms, ensuring the repository's public-facing information is correctly set without exposing platform-specific details in the main workflow.
        """
        pass

    def _get_unauth_url(self, url: str = None) -> str:
        """
        Returns the repository URL without authentication token and ensures it ends with the `.git` extension.
        
        This method is used to normalize repository URLs for consistent internal handling, particularly when interacting with Git operations that expect a standard `.git` suffix. It ensures that the URL is formatted appropriately regardless of whether an authentication token is present in the original input.
        
        Args:
            url: The URL to convert. If None, the original repository URL (`self.repo_url`) is used instead.
        
        Returns:
            The repository URL without authentication token, guaranteed to end with `.git`.
        """
        repo_url = url if url else self.repo_url

        # Ensure the URL ends with .git
        if not repo_url.endswith(".git"):
            repo_url += ".git"

        return repo_url

    def _get_auth_url(self, url: str = None) -> str:
        """
        Converts the repository URL by adding a token for authentication.
        
        This method is used to securely embed an authentication token into a Git repository URL,
        enabling authenticated access for subsequent Git operations (e.g., cloning, fetching).
        If no explicit URL is provided, the method defaults to the repository URL stored in the instance.
        
        Args:
            url: The URL to convert. If None, the method uses the original repository URL (self.repo_url).
        
        Returns:
            The repository URL with the authentication token inserted.
        
        Raises:
            ValueError: If the token is not found in the environment variables or if the repository URL format is unsupported (handled by _build_auth_url).
        """
        if not self.token:
            raise ValueError("Token not found in environment variables.")
        repo_url = url if url else self.repo_url
        return self._build_auth_url(repo_url)

    @abc.abstractmethod
    def _build_auth_url(self, repo_url: str) -> str:
        """
        A platform-specific helper method for converting the repository URL by adding a token for authentication.
        
        This method modifies the provided repository URL to embed an authentication token, enabling secure access to the repository without requiring manual login. This is essential for automated operations within the OSA Tool, such as cloning or fetching repository data, where authentication must be handled programmatically.
        
        Args:
            repo_url: The URL of the Git repository to be authenticated.
        
        Returns:
            The authenticated repository URL with the token embedded.
        """
        pass

    @abc.abstractmethod
    def validate_topics(self, topics: List[str]) -> List[str]:
        """
        Validates topics against platform-specific APIs by checking which ones exist on the platform.
        
        This method is used to filter a list of potential topics, ensuring only those recognized by the platform are retained. This helps maintain accurate metadata and avoid tagging repositories with non-existent or unsupported topics.
        
        Args:
            topics: List of potential topics to validate.
        
        Returns:
            List of validated topics that exist on the platform.
        """
        pass


class GitHubAgent(GitAgent):
    """
    GitHubAgent is a class that provides a comprehensive interface for interacting with GitHub repositories through the GitHub API.
    
        Attributes:
            base_url: The base URL for GitHub API requests.
            token: The authentication token used for API requests.
            headers: The HTTP headers used for API requests, including authentication.
            fork_url: The URL of the forked repository, if a fork has been created.
            repo_metadata: The metadata of the repository being interacted with.
    
        Methods:
            _get_token: Retrieves the authentication token from environment variables.
            _load_metadata: Fetches and loads metadata for a specific repository.
            create_fork: Creates a fork of the specified GitHub repository.
            star_repository: Stars the specified GitHub repository for the authenticated user.
            _check_github_branch_exists: Checks if a branch exists on GitHub using the API.
            post_comment: Posts a comment to a specific GitHub pull request.
            create_pull_request: Creates or updates a pull request on GitHub.
            _update_about_section: Updates the GitHub repository's about section.
            _build_report_url: Constructs a URL pointing to a specific report file on a GitHub fork.
            _build_auth_url: Constructs a GitHub repository URL containing authentication credentials.
            validate_topics: Validates a list of topics against the GitHub Topics API.
    """

    def _get_token(self) -> str:
        """
        Retrieves the authentication token from environment variables.
        
        This method attempts to fetch a token from the 'GIT_TOKEN' environment variable,
        falling back to 'GITHUB_TOKEN' if the former is not set. If neither is found,
        it returns an empty string. This token is used for authenticating requests to
        GitHub's API, enabling operations like repository analysis and enhancements.
        
        Returns:
            str: The retrieved authentication token or an empty string if not found.
        """
        return os.getenv("GIT_TOKEN", os.getenv("GITHUB_TOKEN", ""))

    def _load_metadata(self, repo_url: str) -> RepositoryMetadata:
        """
        Fetches and loads metadata for a specific repository using the GitHub metadata loader.
        This internal method centralizes metadata retrieval to ensure consistent data sourcing for subsequent analysis and documentation tasks.
        
        Args:
            repo_url: The URL of the GitHub repository for which to retrieve metadata.
        
        Returns:
            RepositoryMetadata: An object containing the loaded repository metadata, such as repository name, owner, description, stars, and other platform-specific information.
        """
        return GitHubMetadataLoader.load_data(repo_url)

    def create_fork(self) -> None:
        """
        Creates a fork of the specified GitHub repository using the GitHub API.
        
        This method authenticates using the provided token and sends a POST request to the GitHub API to create a fork of the base repository. If successful, it updates the instance with the URL of the newly created fork. This is typically done to obtain a personal copy of the repository where changes can be made without affecting the original.
        
        Args:
            self: The instance of the GitHubAgent class. The instance must have a valid `token` and `repo_url` already set.
        
        Raises:
            ValueError: If the GitHub token is not provided.
            RuntimeError: If the GitHub API request fails (handled by `_handle_api_error`).
        
        Attributes Initialized:
            fork_url: The web URL (html_url) of the newly created GitHub fork. This is set only upon a successful API response (status code 200 or 202).
        """
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
        """
        Stars the specified GitHub repository for the authenticated user.
        
        This method checks if the repository is already starred by the user. If not, it sends a PUT request to the GitHub API to star the repository. It requires a valid GitHub token and handles API errors gracefully by logging them.
        
        Args:
            repo_url: The URL of the GitHub repository to star. This is derived from the instance's `repo_url` attribute.
            token: The GitHub authentication token. This is derived from the instance's `token` attribute. Required for API authorization.
        
        Raises:
            ValueError: If the GitHub token is not provided.
        
        Why:
            The method first verifies the star status to avoid redundant API calls and unnecessary notifications. If the repository is already starred, it logs the status and exits early. This prevents duplicate starring and respects GitHub's API idempotency for the star action.
        """
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
        """
        Check if a branch exists in a GitHub repository via the GitHub API.
        
        This method determines whether a given branch name exists in either the original
        repository or a forked repository, depending on whether a fork URL is configured.
        It is used to verify branch availability before performing operations such as
        creating pull requests or checking out branches, ensuring that the branch
        is present and accessible.
        
        Args:
            branch: The name of the branch to check for existence.
        
        Returns:
            True if the branch exists (API returns 200), False if it does not exist
            (API returns 404) or if any other error occurs (e.g., network issues,
            authentication problems, or unexpected API responses). In case of
            non‑404 errors, a warning is logged.
        """
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
        """
        Posts a comment to a specific GitHub pull request via the GitHub API.
        
        Args:
            pr_number: The identification number of the pull request where the comment will be posted.
            comment_body: The text content of the comment to be posted.
        
        Why:
        This method enables automated interaction with pull requests, allowing the OSA Tool to provide feedback, notes, or documentation-related messages directly within the GitHub workflow. It supports the tool's goal of enhancing repository maintainability by facilitating communication about changes or improvements.
        """
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
        """
        Creates or updates a pull request on GitHub.
        
        This method implements intelligent PR management:
        1. Checks if an open PR already exists for the current branch.
        2. If a PR exists and there are new reports, updates the PR description
           with all unique report links (removing duplicates).
        3. If no PR exists and changes are present, creates a new PR with all
           available reports from the attachment branch.
        
        WHY: This approach prevents duplicate PRs for the same branch and ensures
        that all generated reports are aggregated into a single PR description,
        improving organization and traceability.
        
        Args:
            title: Optional title for the PR. Uses the last commit message if not provided.
            body: Optional body/description for the PR. If provided when updating an
                  existing PR, this body is posted as a new comment on the PR.
            changes: Boolean flag indicating whether there are changes to report.
                     If False and no PR exists, no action is taken. If True, a new
                     PR is created with available reports.
        
        Raises:
            ValueError: If the GitHub token is not available, preventing API calls.
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
        """
        Updates the GitHub repository's about section, including description, homepage, and topics.
        
        This method performs two separate API calls: a PATCH request to update the repository's
        general information (description and homepage) and a PUT request to update the
        repository's topics. It logs the success of these operations or handles errors
        via the internal error handling mechanism. The two calls are made separately because
        the GitHub API requires updating repository metadata and topics through different endpoints.
        
        Args:
            repo_path: The full path of the repository (e.g., 'owner/repo').
            about_content: A dictionary containing the keys 'description', 'homepage',
                and 'topics' with their respective new values. The 'topics' value must be a list of strings.
        
        Note:
            Errors from either API call are handled without raising exceptions (raise_exception=False),
            allowing partial updates to succeed even if one operation fails. Success is logged for each
            independent update.
        """
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
        """
        Constructs a URL pointing to a specific report file on a GitHub fork.
        
        The method builds a direct URL to a report file stored in a branch of the fork, enabling easy access for viewing or downloading the report. This is used to generate links for reports produced by the OSA Tool's documentation pipeline.
        
        Args:
            report_branch: The name of the branch where the report is located.
            report_filename: The name of the report file.
        
        Returns:
            str: The full URL to the report file on the fork.
        """
        return f"{self.fork_url}/blob/{report_branch}/{report_filename}"

    def _build_auth_url(self, repo_url: str) -> str:
        """
        Constructs a GitHub repository URL containing authentication credentials.
        
        WHY: To enable authenticated Git operations (like cloning or pushing) by embedding the agent's access token directly into the HTTPS URL, which is required when interacting with private repositories or when performing actions that require authentication.
        
        Args:
            repo_url: The original HTTPS URL of the GitHub repository (e.g., "https://github.com/owner/repo").
        
        Returns:
            str: The authenticated URL formatted with the access token for Git operations (e.g., "https://<token>@github.com/owner/repo.git").
        
        Raises:
            ValueError: If the provided repo_url does not start with "https://github.com/", indicating an unsupported or non-GitHub URL format.
        """
        if repo_url.startswith("https://github.com/"):
            repo_path = repo_url[len("https://github.com/") :]
            return f"https://{self.token}@github.com/{repo_path}.git"
        raise ValueError(f"Unsupported repository URL format for GitHub: {repo_url}")

    def validate_topics(self, topics: List[str]) -> List[str]:
        """
        Validates a list of topics against the GitHub Topics API to ensure they exist and meet a minimum repository count.
                
        The method checks each topic by querying the GitHub API. If a topic is found and associated with more than five repositories, it is considered valid. If the API returns a single exact match that differs in casing or formatting, the method applies the transformation to the canonical name. It handles API rate limiting by pausing execution when a 403 status code is encountered.
        
        WHY: This validation ensures that only established, widely-used GitHub topics are applied to a repository, improving discoverability and avoiding the creation of overly niche or misspelled tags.
        
        Args:
            topics: A list of strings representing the topics to be validated.
        
        Returns:
            List[str]: A list of validated and potentially transformed topic names that exist on GitHub. Topics that do not meet the minimum repository count or are not found are omitted.
        """
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
    """
    GitLabAgent provides an interface for interacting with GitLab repositories and performing various operations.
    
        Attributes:
            fork_url: The web URL of the forked repository or the original repository URL if the user is the owner.
    
        Methods:
            _get_token: Retrieves the GitLab authentication token from environment variables.
            _load_metadata: Fetches and loads metadata for a specific repository from GitLab.
            create_fork: Creates a fork of the specified GitLab repository for the authenticated user.
            star_repository: Stars a GitLab repository using the GitLab API.
            _check_gitlab_branch_exists: Checks if a branch exists on GitLab using the API.
            post_note: Posts a comment or note to a specific GitLab merge request.
            create_pull_request: Creates or updates a merge request on GitLab.
            _update_about_section: Updates the GitLab repository's description and topics using the GitLab API.
            _build_report_url: Constructs a URL pointing to a specific report file on a Git fork.
            _build_auth_url: Constructs a GitLab authentication URL using an OAuth2 token.
            validate_topics: Validates a list of topics against the GitLab Topics API.
    """

    def _get_token(self) -> str:
        """
        Retrieves the GitLab authentication token from environment variables.
                
                The method checks for the 'GITLAB_TOKEN' environment variable first, falling back to 'GIT_TOKEN' if the former is not set. If neither is found, it returns an empty string.
                This approach allows flexible token configuration, supporting both GitLab-specific and generic Git environment variable names.
                
                Returns:
                    str: The authentication token or an empty string if not found.
        """
        return os.getenv("GITLAB_TOKEN", os.getenv("GIT_TOKEN", ""))

    def _load_metadata(self, repo_url: str) -> RepositoryMetadata:
        """
        Fetches and loads metadata for a specific repository from GitLab.
        
        This method delegates to a dedicated loader class to retrieve structured metadata
        (such as project details, contributors, issues, or other repository attributes)
        from the GitLab API. This separation allows the agent to focus on orchestration
        while keeping data-fetching logic centralized and reusable.
        
        Args:
            repo_url: The URL of the GitLab repository for which to retrieve metadata.
        
        Returns:
            RepositoryMetadata: An object containing the loaded repository metadata.
        """
        return GitLabMetadataLoader.load_data(repo_url)

    def create_fork(self) -> None:
        """
        Creates a fork of the specified GitLab repository for the authenticated user.
        
        This method validates the presence of a GitLab token, extracts the GitLab instance and project path from the repository URL, and checks if the current user already owns the repository or has an existing fork. If no fork exists, it initiates a fork request via the GitLab API. The method ensures the user does not create duplicate forks and efficiently reuses an existing fork or the original repository when appropriate.
        
        Args:
            self: The instance of the GitLabAgent class.
        
        Attributes Initialized:
            fork_url: The web URL of the forked repository. If the user already owns the original repository, this is set to the original repository URL. If a fork already exists for the user, this is set to that fork's web URL.
        
        Raises:
            ValueError: If the GitLab token is missing, user information cannot be retrieved, the forks list cannot be accessed, or the fork creation request fails.
        
        Why:
            Forking is a prerequisite for many collaborative workflows (e.g., submitting merge requests). This method automates the fork creation while avoiding unnecessary API calls and duplicate forks by first checking ownership and existing forks.
        """
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
        """
        Stars a GitLab repository using the GitLab API.
        
        This method extracts the GitLab instance and project path from the repository URL and sends a POST request to the star endpoint. It handles cases where the repository is already starred or successfully starred, and logs an error if the request fails. The method relies on the instance's `repo_url` and `token` attributes.
        
        Args:
            self: The instance of the GitLabAgent class.
        
        Raises:
            ValueError: If the GitLab token is not provided.
        
        Why:
            The method performs URL parsing to construct the correct API endpoint because the GitLab API requires the project path to be URL-encoded and uses a specific endpoint structure (/api/v4/projects/{project_path}/star). It checks for status codes 304 (already starred) and 201 (successfully starred) to provide appropriate logging without raising exceptions for these expected outcomes.
        """
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
        """
        Check if a branch exists on a GitLab repository via the GitLab API.
        
        This method constructs the appropriate API endpoint for the target GitLab project
        and issues a GET request to determine whether the specified branch exists.
        It handles both the original repository and a forked repository, depending on
        whether a fork URL is configured. The method is used internally to verify
        branch presence before performing operations that depend on branch existence,
        such as creating merge requests or checking out code.
        
        Args:
            branch: The name of the branch to check for existence.
        
        Returns:
            True if the branch exists (API returns 200), False if the branch does not
            exist (API returns 404) or if an error occurs (e.g., network issue, unexpected
            API response, or authentication failure). Warnings are logged for non‑404
            errors or exceptions.
        """
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
        """
        Posts a comment or note to a specific GitLab merge request via the GitLab API.
        
        Args:
            project_id: The ID of the GitLab project.
            mr_iid: The internal ID (IID) of the merge request within the project.
            note_body: The content of the note or comment to be posted.
        
        Why:
            This method enables automated interaction with merge requests, such as posting review feedback, status updates, or bot-generated messages, which is essential for integrating automated documentation and analysis workflows into the GitLab merge request process.
        
        Note:
            The GitLab instance URL and authentication token are derived from the class instance's `repo_url` and `token` attributes. The request is authenticated using a Bearer token.
        """
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
        """
        Creates or updates a merge request on GitLab.
        
        This method implements intelligent MR management:
        1. Checks if an open MR already exists for the current branch.
        2. If an MR exists and there are new reports, updates the MR description
           with all unique report links (removing duplicates) and appends a new note
           if a body is provided.
        3. If no MR exists and there are changes to commit, creates a new MR with
           all available reports from the attachment branch.
        
        The method ensures that the MR description contains a consolidated list of
        generated report links, avoiding duplicates, and includes a signature to
        identify agent‑generated content.
        
        Args:
            title: Optional title for the MR. Uses the last commit message if not provided.
            body: Optional body/description for the MR. If provided and an MR exists,
                  this content is posted as a new note on the existing MR.
            changes: Flag indicating whether there are changes to commit. A new MR is
                     created only when this flag is True and no open MR exists.
        
        Raises:
            ValueError: If the GitLab token is missing, if project information cannot
                        be retrieved, or if MR creation fails (unless the MR already exists).
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
        """
        Updates the GitLab repository's description and topics using the GitLab API.
        
        This method extracts the GitLab instance URL from the repository URL stored in the class instance, formats the provided repository path for API compatibility, and sends a PUT request to update the project's metadata with the given description and topics. The update is performed using a personal access token for authentication.
        
        Args:
            repo_path: The full path or namespace of the repository on GitLab (e.g., "username/project").
            about_content: A dictionary containing the new metadata. Must include the keys "description" (the new repository description) and "topics" (a list of topic tags to apply). The topics are sent to the API as "tag_list".
        
        Why:
            The method exists to programmatically update the repository's "About" section (description and topics) via the GitLab REST API, enabling automated repository maintenance as part of the OSA Tool's enhancement pipeline. The path is URL-encoded (replacing "/" with "%2F") to meet GitLab API requirements for project identification.
        """
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
        """
        Constructs a URL pointing to a specific report file on a Git fork.
        
        This method builds a direct web URL to a report file stored in a specific branch of the forked repository. It is used to generate accessible links for viewing or sharing reports produced by the OSA Tool's documentation pipeline.
        
        Args:
            report_branch: The name of the branch where the report is located.
            report_filename: The name of the report file.
        
        Returns:
            str: The complete URL to the report file on the fork. The URL format is: {fork_url}/-/blob/{report_branch}/{report_filename}
        """
        return f"{self.fork_url}/-/blob/{report_branch}/{report_filename}"

    def _build_auth_url(self, repo_url: str) -> str:
        """
        Constructs a GitLab authentication URL using an OAuth2 token.
        
        This method parses a standard GitLab repository URL and injects the instance's
        token into the URL structure to allow for authenticated git operations.
        It specifically transforms the URL to embed the token in the format required
        for Git to authenticate via HTTPS without interactive prompts.
        
        Args:
            repo_url: The original GitLab repository URL to be transformed. Must be a valid
                      GitLab URL matching the pattern `https?://([^/]*gitlab[^/]*)/(.+)`.
        
        Returns:
            str: A formatted URL string containing the OAuth2 credentials and the repository path,
                 with `.git` appended to the path.
        
        Raises:
            ValueError: If the provided `repo_url` does not match the expected GitLab URL pattern.
        """
        gitlab_match = re.match(r"https?://([^/]*gitlab[^/]*)/(.+)", repo_url)
        if gitlab_match:
            gitlab_host = gitlab_match.group(1)
            repo_path = gitlab_match.group(2)
            return f"https://oauth2:{self.token}@{gitlab_host}/{repo_path}.git"
        raise ValueError(f"Unsupported repository URL format for GitLab: {repo_url}")

    def validate_topics(self, topics: List[str]) -> List[str]:
        """
        Validates a list of topics against the GitLab Topics API.
        
        This method checks each provided topic string by querying the GitLab API. It verifies if an exact match for the topic name exists. It handles API rate limiting by pausing execution and includes error handling for network or request failures.
        
        Args:
            topics: A list of strings representing the topics to be validated.
        
        Returns:
            A list containing only the topics that were successfully validated against the GitLab API.
        
        Why:
            The validation ensures that only existing, official GitLab topics are used, which helps maintain consistency and discoverability when tagging repositories. The method includes rate‑limit handling and delays between requests to comply with GitLab API usage policies and to avoid being blocked.
        """
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
    """
    GitverseAgent provides an interface for interacting with Gitverse repositories via API.
    
        This class handles authentication, repository operations (forking, starring), pull request management, and metadata loading for Gitverse repositories. It also includes utilities for constructing URLs and validating repository topics.
    
        Attributes:
            token: Authentication token for Gitverse API access.
            base_repo_url: URL of the base repository being operated on.
            fork_url: URL of the user's fork of the base repository.
            repo_metadata: Loaded metadata for the repository.
            user_info: Information about the authenticated user.
    
        Methods:
            _get_token: Retrieves the authentication token from environment variables.
            _load_metadata: Loads metadata for a specific repository using the Gitverse loader.
            create_fork: Creates a fork of the repository on Gitverse.
            star_repository: Stars a repository on Gitverse for the authenticated user.
            _check_gitverse_branch_exists: Check if branch exists on Gitverse using API.
            create_pull_request: Creates or updates a pull request on Gitverse.
            _update_about_section: Logs a warning regarding the lack of support for updating the repository About section.
            _build_report_url: Constructs a URL pointing to a specific report file within a repository fork.
            _build_auth_url: Constructs an authenticated URL for a Gitverse repository using the stored token.
            validate_topics: Validates a list of topics for the Gitverse platform.
    """

    def _get_token(self) -> str:
        """
        Retrieves the authentication token from environment variables.
        
        The method checks for the 'GITVERSE_TOKEN' environment variable first, falling back to 'GIT_TOKEN' if the former is not set. This order allows a project-specific token to override a general-purpose token. If neither is found, it returns an empty string.
        
        Returns:
            str: The authentication token or an empty string if not found.
        """
        return os.getenv("GITVERSE_TOKEN", os.getenv("GIT_TOKEN", ""))

    def _load_metadata(self, repo_url: str) -> RepositoryMetadata:
        """
        Loads metadata for a specific repository using the Gitverse loader.
        This method is used internally to fetch structured metadata (such as repository details, contributors, and activity) required for subsequent documentation and enhancement operations.
        
        Args:
            repo_url: The URL of the repository for which to load metadata.
        
        Returns:
            RepositoryMetadata: An object containing the metadata for the repository.
        """
        return GitverseMetadataLoader.load_data(repo_url)

    def create_fork(self) -> None:
        """
        Creates a fork of the repository on Gitverse.
        
        This method authenticates with the Gitverse API using the provided token to create a fork of the base repository. It first checks if the current user is already the owner of the repository. If not, it checks if a fork already exists for the user. If no fork exists, it sends a request to create one. The resulting fork URL is stored in the instance.
        
        Why this logic is used: It avoids unnecessary API calls and prevents duplicate forks by first verifying ownership and then checking for an existing fork before attempting creation.
        
        Args:
            self: The instance of the GitverseAgent class.
        
        Attributes Initialized:
            fork_url: The URL of the created or existing fork on Gitverse. If the user already owns the repository, this is set to the original repo_url.
        
        Raises:
            ValueError: If the Gitverse token is missing, user information cannot be retrieved, or the fork creation request fails.
        """
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
        """
        Stars a repository on Gitverse for the authenticated user.
        
        This method checks if the repository is already starred by the user. If not, it sends a request to the Gitverse API to star the repository. It requires a valid authentication token and repository URL to be present on the instance.
        
        The method first verifies the token exists, then constructs the API URL from the repository URL. It performs a GET request to check the current star status. If the repository is already starred (status 204), it logs this and returns early. If the check fails for any reason other than a 404 (which indicates the repository is not starred), it raises an error. Finally, if the repository is not starred, it sends a PUT request to star it.
        
        Args:
            self: The instance of the GitverseAgent class. The instance must have `token` and `repo_url` attributes set.
        
        Raises:
            ValueError: If the Gitverse token is missing, if the initial GET request to check star status fails (with a status code other than 404), or if the subsequent PUT request to star the repository fails.
        """
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
        """
        Check if a branch exists on Gitverse using the API.
        
        WHY: This method is used to verify whether a specific branch exists in the repository before performing operations that depend on branch availability (e.g., creating pull requests, merging). It ensures that the agent can safely proceed with branch-related tasks.
        
        Args:
            branch: The name of the branch to check for existence.
        
        Returns:
            True if the branch exists on Gitverse, False otherwise. Returns False if the API request fails or returns a non-200 status code.
        
        The method determines which repository URL to check (either the original repo or the fork URL) based on whether a fork URL is set. It then constructs the API endpoint, adds necessary headers (including an authorization token if available), and makes a GET request. If the request succeeds (status 200), it parses the response to see if the branch name matches any in the list.
        """
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
        """
        Creates or updates a pull request on Gitverse.
        
                This method implements intelligent PR management:
                1. Checks if an open PR already exists for the current branch.
                2. If a PR exists and there are new reports, updates the PR description
                   with all unique report links (removing duplicates) while preserving
                   the existing description text and any new body content.
                3. If no PR exists and there are changes to commit, creates a new PR
                   with all available reports from the attachment branch.
        
                The method ensures that the PR description always contains a complete,
                   deduplicated list of report links and is signed with the agent's signature.
        
                Args:
                    title: Optional title for the PR. Uses the last commit message if not provided.
                    body: Optional body/description for the PR. If provided when updating an existing PR,
                          this content is appended to the existing description (if not already present).
                    changes: Flag indicating whether there are changes to commit. A new PR is created
                             only if this flag is True and no open PR exists for the branch.
        
                Raises:
                    ValueError: If the Gitverse token is not set, or if PR creation fails
                                (unless the failure is due to an existing PR).
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
        """
        Logs a warning regarding the lack of support for updating the repository About section.
        
        Currently, Gitverse does not support updating the About section via API. This method
        notifies the user that suggestions for these updates can be viewed in the Pull Request.
        WHY: This method exists as a placeholder to inform users that the intended update operation is not yet implemented, preventing silent failures and guiding them to alternative review locations.
        
        Args:
            repo_path: The path or identifier of the repository to be updated.
            about_content: A dictionary containing the metadata for the About section.
        """
        logger.warning(
            "Updating repository 'About' section via API is not yet supported for Gitverse. You can see suggestions in PR."
        )

    def _build_report_url(self, report_branch: str, report_filename: str) -> str:
        """
        Constructs a URL pointing to a specific report file within a repository fork.
        
        This method builds a direct URL to access a report file stored in a specific branch of the fork. It is used internally to generate links for retrieving or referencing generated documentation and analysis reports.
        
        Args:
            report_branch: The name of the branch where the report is located.
            report_filename: The name of the report file to be accessed.
        
        Returns:
            str: The complete URL for the specified report file, formatted as `{fork_url}/content/{report_branch}/{report_filename}`.
        """
        return f"{self.fork_url}/content/{report_branch}/{report_filename}"

    def _build_auth_url(self, repo_url: str) -> str:
        """
        Constructs an authenticated URL for a Gitverse repository using the stored token.
        
        Args:
            repo_url: The original HTTPS URL of the Gitverse repository. Must start with "https://gitverse.ru/".
        
        Returns:
            str: The repository URL with the authentication token embedded in the format "https://{token}@gitverse.ru/{repo_path}.git".
        
        Raises:
            ValueError: If the provided repository URL does not start with the expected Gitverse prefix "https://gitverse.ru/". This ensures the method only processes URLs from the correct Gitverse domain.
        
        Why:
            This method enables secure, authenticated access to private Gitverse repositories by embedding the agent's stored token directly into the URL. It transforms a standard HTTPS URL into one that includes authentication credentials, allowing subsequent Git operations (like cloning or fetching) to proceed without separate credential prompts.
        """
        if repo_url.startswith("https://gitverse.ru/"):
            repo_path = repo_url[len("https://gitverse.ru/") :]
            return f"https://{self.token}@gitverse.ru/{repo_path}.git"
        raise ValueError(f"Unsupported repository URL format for Gitverse: {repo_url}")

    def validate_topics(self, topics: List[str]) -> List[str]:
        """
        Validates a list of topics for the Gitverse platform.
        
        Note:
            This method is currently a placeholder and does not perform actual validation. It logs a warning and returns the input list unchanged. This allows the broader OSA Tool pipeline to proceed without interruption while the Gitverse-specific validation logic is under development.
        
        Args:
            topics: A list of strings representing the topics to be validated.
        
        Returns:
            The original list of topics provided as input.
        """
        logger.warning("Topic validation is not yet implemented for Gitverse. Returning original topics list.")
        return topics
