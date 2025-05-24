import os

import requests
from dotenv import load_dotenv
from git import GitCommandError, InvalidGitRepositoryError, Repo

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.utils import get_base_repo_url, logger, parse_folder_name


class GithubAgent:
    """A class to interact with GitHub repositories.

    This class provides functionality to clone repositories, create and checkout branches,
    commit and push changes, and create pull requests.

    Attributes:
        AGENT_SIGNATURE: A signature string appended to pull request descriptions.
        repo_url: The URL of the GitHub repository.
        base_branch: The name of the repository's branch.
        clone_dir: The directory where the repository will be cloned.
        branch_name: The name of the branch to be created.
        repo: The GitPython Repo object representing the repository.
        token: The GitHub token for authentication.
    """

    AGENT_SIGNATURE = (
        "\n\n---\n*This PR was created by [osa_tool](https://github.com/aimclub/OSA).*"
        "\n_OSA just makes your open source project better!_"
    )

    def __init__(self, repo_url: str, repo_branch_name: str = None, branch_name: str = "osa_tool"):
        """Initializes the GithubAgent with the repository URL and branch name.

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
        self.token = os.getenv("GIT_TOKEN")
        self.fork_url = None
        self.metadata = load_data_metadata(self.repo_url)
        self.base_branch = repo_branch_name or self.metadata.default_branch
        self.pr_report_body = ""

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
                logger.info(
                    f"Cloning the {self.base_branch} branch from {self.repo_url} into directory {self.clone_dir}...")
                self.repo = Repo.clone_from(
                    url=self._get_auth_url(),
                    to_path=self.clone_dir,
                    branch=self.base_branch,
                    single_branch=True)
                logger.info("Cloning completed")
            except GitCommandError as e:
                logger.error(f"Cloning failed: {repr(e)}")
                raise

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
            self.repo.git.checkout('-b', branch)
            logger.info(f"Switched to branch {branch}.")

    def commit_and_push_changes(self, branch: str = None, commit_message: str = "osa_tool recommendations") -> bool:
        """Commits and pushes changes to the forked repository.

        Args:
            branch: The name of the branch to push changes to. Defaults to `branch_name`.
            commit_message: The commit message. Defaults to "osa_tool recommendations".
        """
        if not self.fork_url:
            raise ValueError("Fork URL is not set. Please create a fork first.")
        if branch is None:
            branch = self.branch_name

        logger.info("Committing changes...")
        self.repo.git.add('.')
        self.repo.git.commit('-m', commit_message)
        logger.info("Commit completed.")

        logger.info(f"Pushing changes to branch {branch} in fork...")
        self.repo.git.remote('set-url', 'origin', self._get_auth_url(self.fork_url))
        try:
            self.repo.git.push('--set-upstream', 'origin',
                               branch, force_with_lease=True)
            logger.info("Push completed.")
            return True
        except GitCommandError as e:
            raise

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
        pr_body += self.pr_report_body
        pr_body += self.AGENT_SIGNATURE

        pr_data = {
            "title": pr_title,
            "head": f"{self.fork_url.split('/')[-2]}:{self.branch_name}",
            "base": self.base_branch,
            "body": pr_body,
            "maintainer_can_modify": True
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

    def upload_report(
        self,
        report_filename: str,
        report_filepath: str,
        report_branch: str = "osa_tool_attachments",
        commit_message: str = "upload pdf report",
    ) -> None:
        """Uploads the generated PDF report to a separate branch.

        Args:
            report_filename: The name of the report file.
            report_branch: Name of the branch for storing reports. Defaults to "osa_tool_attachments".
            commit_message: Commit message for the report upload. Defaults to "upload pdf report".
        """
        try:
            self.create_and_checkout_branch(report_branch)
        except GitCommandError:
            logger.warning(
                f"PDF report located in the {self.branch_name} branch, moving it."
            )
            with open(report_filepath, "rb") as f:
                preserved_content = f.read()
            self.repo.git.checkout("-f", report_branch)
            with open(report_branch, "wb") as f:
                f.write(preserved_content)
            logger.info(f"Sucessfuly moved PDF report to {report_branch} branch.")

        try:
            self.commit_and_push_changes(report_branch, commit_message)
        except GitCommandError:
            logger.warning(
                "Branch already exists in the fork. Comparing last commit message..."
            )
            last_commit = self.repo.refs[report_branch].commit
            if last_commit.message == "upload pdf report\n":
                logger.warning(
                    f"Commit matches. Force pushing new PDF report to {report_branch} branch of the fork."
                )
                self.repo.git.push(
                    "--set-upstream", "origin", report_branch, force=True
                )
                logger.info("Push completed.")
            else:
                logger.error(
                    "Commit does not match the default, aborting upload report."
                )

        self.create_and_checkout_branch()  # Return to original branch

        report_url = f"{self.fork_url}/blob/{report_branch}/{report_filename}"
        self.pr_report_body = f"\nGenerated report - [{report_filename}]({report_url})\n"

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
            auth_url = f"https://{self.token}@github.com/{repo_path}.git"
            return auth_url
        else:
            raise ValueError("Unsupported repository URL format.")
