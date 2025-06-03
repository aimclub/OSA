import pytest
from unittest.mock import patch


@patch("osa_tool.github_agent.github_agent.requests.post")
def test_create_fork_success(mock_post, github_agent):
    # Arrange
    github_agent.token = "test_token"
    mock_post.return_value.status_code = 202
    mock_post.return_value.json.return_value = {"html_url": "https://github.com/testuser/testrepo-fork"}
    # Act
    github_agent.create_fork()
    # Assert
    assert github_agent.fork_url == "https://github.com/testuser/testrepo-fork"


@patch("osa_tool.github_agent.github_agent.requests.post")
def test_create_fork_error(mock_post, github_agent):
    # Arrange
    github_agent.token = "test_token"
    mock_post.return_value.status_code = 400
    # Assert
    with pytest.raises(ValueError, match="Failed to create fork."):
        github_agent.create_fork()
