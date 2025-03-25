import pytest
from unittest.mock import patch, MagicMock
from git import InvalidGitRepositoryError, GitCommandError, Repo

from osa_tool.github_agent.github_agent import GithubAgent


@pytest.fixture
def github_agent():
    agent = GithubAgent(repo_url="https://github.com/testuser/testrepo")
    agent.repo = MagicMock(Repo)
    return agent


class TestGithubAgent:
    @pytest.mark.parametrize(
        "method, exception_message",
        [
            ("create_fork", "GitHub token is required to create a fork."),
            ("star_repository",
             "GitHub token is required to star the repository."),
            ("create_pull_request",
             "GitHub token is required to create a pull request."),
            ("_get_auth_url", "Token not found in environment variables."),
        ]
    )
    def test_methods_require_token(self, method, exception_message,
                                   github_agent):
        """Test that all methods raise an exception when the GitHub token is missing."""
        github_agent.token = None
        with pytest.raises(ValueError, match=exception_message):
            getattr(github_agent, method)()

    @patch("osa_tool.github_agent.github_agent.requests.post")
    def test_create_fork(self, mock_post, github_agent):
        github_agent.token = "test_token"
        mock_post.return_value.status_code = 202
        mock_post.return_value.json.return_value = {
            "html_url": "https://github.com/testuser/testrepo-fork"
        }
        github_agent.create_fork()
        assert github_agent.fork_url == "https://github.com/testuser/testrepo-fork"

    @patch("osa_tool.github_agent.github_agent.requests.post")
    def test_create_fork_error(self, mock_post, github_agent):
        github_agent.token = "test_token"
        mock_post.return_value.status_code = 400
        with pytest.raises(ValueError, match="Failed to create fork."):
            github_agent.create_fork()

    @patch("osa_tool.github_agent.github_agent.requests.get")
    @patch("osa_tool.github_agent.github_agent.requests.put")
    def test_star_repository_already_stars(self, mock_put, mock_get, github_agent):
        github_agent.token = "test_token"
        mock_get.return_value.status_code = 204
        github_agent.star_repository()
        mock_put.assert_not_called()

    @patch("osa_tool.github_agent.github_agent.requests.get")
    @patch("osa_tool.github_agent.github_agent.requests.put")
    def test_star_repository_adds_star(self, mock_put, mock_get, github_agent):
        github_agent.token = "test_token"
        mock_get.return_value.status_code = 404
        mock_put.return_value.status_code = 204
        github_agent.star_repository()
        mock_put.assert_called_once()

    @patch("osa_tool.github_agent.github_agent.requests.get")
    @patch("osa_tool.github_agent.github_agent.requests.put")
    def test_star_repository_error(self, mock_put, mock_get, github_agent):
        github_agent.token = "test_token"
        mock_get.return_value.status_code = 404
        mock_put.return_value.status_code = 400
        with pytest.raises(ValueError, match="Failed to star repository."):
            github_agent.star_repository()

    @patch("osa_tool.github_agent.github_agent.requests.get")
    def test_star_repository_request_error(self, mock_get, github_agent):
        github_agent.token = "test_token"
        mock_get.return_value.status_code = 500
        with pytest.raises(ValueError, match="Failed to check star status."):
            github_agent.star_repository()

    @patch("osa_tool.github_agent.github_agent.Repo")
    @patch("osa_tool.github_agent.github_agent.logger")
    def test_clone_repository_already_initialized(self, mock_logger, mock_repo, github_agent):
        github_agent.clone_repository()
        mock_logger.warning.assert_called_once_with(f"Repository is already initialized ({github_agent.repo_url})")
        mock_repo.assert_not_called()

    @patch("osa_tool.github_agent.github_agent.Repo")
    @patch("osa_tool.github_agent.github_agent.logger")
    @patch("osa_tool.github_agent.github_agent.os.path.exists")
    def test_clone_repository_directory_exists_invalid_repo(
            self,
            mock_exists,
            mock_logger,
            mock_repo,
            github_agent
    ):
        github_agent.repo = None
        mock_exists.return_value = True
        mock_repo.side_effect = InvalidGitRepositoryError("Not a git repo")
        with pytest.raises(InvalidGitRepositoryError):
            github_agent.clone_repository()

        mock_logger.error.assert_called_once_with(f"Directory {github_agent.clone_dir} exists but is not a valid Git repository")

    @patch("osa_tool.github_agent.github_agent.Repo")
    @patch("osa_tool.github_agent.github_agent.logger")
    @patch("osa_tool.github_agent.github_agent.os.path.exists")
    def test_clone_repository_clone_new_repo(self, mock_exists, mock_logger,
                                             mock_repo, github_agent):
        github_agent.repo = None
        mock_exists.return_value = False
        mock_repo.clone_from.return_value = MagicMock()

        github_agent.clone_repository()
        mock_repo.clone_from.assert_called_once_with(
            github_agent._get_auth_url(), github_agent.clone_dir)

        mock_logger.info.assert_any_call(f"Cloning repository {github_agent.repo_url} into {github_agent.clone_dir}...")

    @patch("osa_tool.github_agent.github_agent.Repo")
    @patch("osa_tool.github_agent.github_agent.logger")
    @patch("osa_tool.github_agent.github_agent.os.path.exists")
    def test_clone_repository_clone_error(self, mock_exists, mock_logger,
                                          mock_repo, github_agent):
        github_agent.repo = None
        mock_exists.return_value = False
        mock_repo.clone_from.side_effect = GitCommandError("Cloning failed", "git")
        with pytest.raises(GitCommandError):
            github_agent.clone_repository()

        mock_logger.error.assert_called_once_with("Cloning failed: GitCommandError('Cloning failed', 'git')")

    def test_commit_and_push_changes_success(self, github_agent):
        github_agent.fork_url = "https://github.com/testuser/testrepo-fork"
        github_agent.branch_name = "feature-branch"

        with patch.object(
                github_agent,
                "_get_auth_url",
                return_value="https://auth-url.com") as mock_auth_url, \
                patch("osa_tool.github_agent.github_agent.logger") as mock_logger:

            github_agent.repo.git.add = MagicMock()
            github_agent.repo.git.commit = MagicMock()
            github_agent.repo.git.remote = MagicMock()
            github_agent.repo.git.push = MagicMock()

            github_agent.commit_and_push_changes(commit_message="Test commit")

            github_agent.repo.git.add.assert_called_once_with('.')
            github_agent.repo.git.commit.assert_called_once_with('-m', "Test commit")
            github_agent.repo.git.push.assert_called_once_with(
                '--set-upstream',
                'origin',
                "feature-branch",
                force_with_lease=True
            )

            mock_logger.info.assert_any_call("Committing changes...")
            mock_logger.info.assert_any_call("Commit completed.")
            mock_logger.info.assert_any_call("Pushing changes to branch feature-branch in fork...")
            mock_logger.info.assert_any_call("Push completed.")

    def test_commit_and_push_changes_no_fork_url(self, github_agent):
        github_agent.fork_url = None
        with pytest.raises(ValueError, match="Fork URL is not set. Please create a fork first."):
            github_agent.commit_and_push_changes()
