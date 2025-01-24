from git import Repo, GitCommandError, InvalidGitRepositoryError
import os
import logging
import requests
from dotenv import load_dotenv
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)


class GithubAgent:
    def __init__(self, repo_url: str, branch_name: str = "OSA"):
        """
        Initializes GithubAgent.

        :param repo_url: URL of the repository.
        :param branch_name: Name of the branch to be created.
        """
        load_dotenv()
        self.repo_url = repo_url
        self.clone_dir = repo_url.rstrip('/').split('/')[-1]
        self.branch_name = branch_name
        self.repo = None
        self.token = os.getenv("GIT_TOKEN")

    def clone_repository(self) -> None:
        """
        Clones the repository into the specified directory if it doesn't exist locally.
        If the repository already exists locally, initializes it.

        :raises InvalidGitRepositoryError: If the local directory exists but is not a valid Git repository.
        :raises GitCommandError: If cloning the repository fails.
        """
        if self.repo:
            logging.warning("Repository already initialized")
            return

        if os.path.exists(self.clone_dir):
            try:
                logging.info(f"Repository already exists at {self.clone_dir}. Initializing...")
                self.repo = Repo(self.clone_dir)
                logging.info("Repository initialized from existing directory")
            except InvalidGitRepositoryError:
                logging.error(f"Directory {self.clone_dir} exists but is not a valid Git repository")
                raise
        else:
            try:
                logging.info(f"Cloning repository {self.repo_url} into {self.clone_dir}...")
                self.repo = Repo.clone_from(self._get_auth_url(), self.clone_dir)
                logging.info("Cloning completed")
            except GitCommandError as e:
                logging.error(f"Cloning failed: {str(e)}")
                raise

    def create_and_checkout_branch(self) -> None:
        """Creates and switches to a new branch."""
        if self.branch_name in self.repo.heads:
            logging.info(f"Branch {self.branch_name} already exists. Switching to it...")
            self.repo.git.checkout(self.branch_name)
            return
        else:
            logging.info(f"Creating and switching to branch {self.branch_name}...")
            self.repo.git.checkout('-b', self.branch_name)
            logging.info(f"Switched to branch {self.branch_name}.")

    def commit_and_push_changes(self, commit_message: str = "OSA recommendations") -> None:
        """Commits and pushes changes to the remote branch."""
        logging.info("Committing changes...")
        self.repo.git.add('.')
        self.repo.git.commit('-m', commit_message)
        logging.info("Commit completed.")

        logging.info(f"Pushing changes to branch {self.branch_name}...")
        self.repo.git.push('--set-upstream', 'origin', self.branch_name)
        logging.info("Push completed.")

    def create_pull_request(self, base_branch: str = "main", title: str = None, body: str = None) -> None:
        """
        Creates a pull request from the current branch to the specified base branch.

        :param base_branch: The branch into which the PR should be merged (default is 'main').
        :param title: The title of the PR. If None, the commit message will be used.
        :param body: The body/description of the PR. If None, the commit message will be used.
        :raises ValueError: If the GitHub token is not set or the API request fails.
        """
        if not self.token:
            raise ValueError("GitHub token is required to create a pull request.")

        base_repo = self.repo_url[len("https://github.com/"):].rstrip('/')
        last_commit = self.repo.head.commit
        pr_title = title if title else last_commit.message
        pr_body = body if body else last_commit.message

        # Формируем данные для создания PR
        pr_data = {
            "title": pr_title,
            "head": self.branch_name,
            "base": base_branch,
            "body": pr_body
        }

        # Отправляем запрос к GitHub API
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"https://api.github.com/repos/{base_repo}/pulls"
        response = requests.post(url, json=pr_data, headers=headers)

        if response.status_code == 201:
            logging.info(f"Pull request created successfully: {response.json()['html_url']}")
        else:
            logging.error(f"Failed to create pull request: {response.status_code} - {response.text}")
            raise ValueError("Failed to create pull request.")

    def _get_auth_url(self) -> str:
        """
        Converts the repository URL by adding a token for authentication.
        :return: Repository URL with the token.
        """
        if not self.token:
            raise ValueError("Token not found in environment variables.")

        if self.repo_url.startswith("https://github.com/"):
            repo_path = self.repo_url[len("https://github.com/"):]
            auth_url = f"https://{self.token}@github.com/{repo_path}.git"
            return auth_url
        else:
            raise ValueError("Unsupported repository URL format.")
