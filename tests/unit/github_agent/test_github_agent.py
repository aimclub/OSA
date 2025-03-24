import os
import pytest
import requests
from unittest.mock import patch, MagicMock
from osa_tool.github_agent.github_agent import GithubAgent
from git.exc import InvalidGitRepositoryError, GitCommandError

@pytest.fixture
def github_agent():
    return GithubAgent(repo_url="https://github.com/testuser/testrepo")


class TestGithubAgent:
    @pytest.mark.parametrize(
        "method, exception_message",
        [
            ("create_fork", "GitHub token is required to create a fork."),
            ("star_repository", "GitHub token is required to star the repository."),
            ("create_pull_request", "GitHub token is required to create a pull request."),
            ("_get_auth_url", "Token not found in environment variables."),
        ]
    )
    def test_methods_require_token(self, method, exception_message, github_agent):
        """Test that all methods raise an exception when the GitHub token is missing."""

        # Set token to None for each test method
        github_agent.token = None

        # Call the method and check for the ValueError with the expected message
        with pytest.raises(ValueError, match=exception_message):
            getattr(github_agent, method)()

    @patch("osa_tool.github_agent.github_agent.requests.post")
    def test_create_fork(self, mock_post, github_agent):
        # Checks successful creation of a fork
        github_agent.token = "test_token"
        mock_post.return_value.status_code = 202
        mock_post.return_value.json.return_value = {"html_url": "https://github.com/testuser/testrepo-fork"}

        github_agent.create_fork()
        assert github_agent.fork_url == "https://github.com/testuser/testrepo-fork"

        # Checks for an error case when creating a fork
        mock_post.return_value.status_code = 400
        with pytest.raises(ValueError, match="Failed to create fork."):
            github_agent.create_fork()

    @patch("osa_tool.github_agent.github_agent.requests.get")
    @patch("osa_tool.github_agent.github_agent.requests.put")
    def test_star_repository(self, mock_put, mock_get, github_agent):
        github_agent.token = "test_token"

        # Checks that if the repository is already starred, then do nothing
        mock_get.return_value.status_code = 204
        github_agent.star_repository()
        mock_put.assert_not_called()

        # Checks if starred was successfully added
        mock_get.return_value.status_code = 404
        mock_put.return_value.status_code = 204
        github_agent.star_repository()
        mock_put.assert_called_once()

        # Checks for an error when starring a repository
        mock_put.return_value.status_code = 400
        with pytest.raises(ValueError, match="Failed to star repository."):
            github_agent.star_repository()

        # Checks for an error when making a request
        mock_get.return_value.status_code = 500
        with pytest.raises(ValueError, match="Failed to check star status."):
            github_agent.star_repository()
