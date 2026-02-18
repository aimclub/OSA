import pytest
from unittest.mock import patch


@patch("osa_tool.git_agent.git_agent.requests.post")
def test_create_fork_success(mock_post, github_agent):
    """
    Test that GitHubAgent.create_fork successfully sets the fork_url when the GitHub API
    returns a 202 status code and provides a JSON payload containing the fork's HTML URL.
    
    Parameters
    ----------
    mock_post : MagicMock
        The mocked requests.post function provided by the @patch decorator.
    github_agent : GitHubAgent
        The GitHubAgent instance whose create_fork method is being tested.
    
    Returns
    -------
    None
    """
    # Arrange
    github_agent.token = "test_token"
    mock_post.return_value.status_code = 202
    mock_post.return_value.json.return_value = {"html_url": "https://github.com/testuser/testrepo-fork"}
    # Act
    github_agent.create_fork()
    # Assert
    assert github_agent.fork_url == "https://github.com/testuser/testrepo-fork"


@patch("osa_tool.git_agent.git_agent.requests.post")
def test_create_fork_error(mock_post, github_agent):
    """
    Test that creating a fork raises a ValueError when the GitHub API returns a 400 status code.
    
    Parameters
    ----------
    mock_post : MagicMock
        Mocked requests.post function patched by the test.
    github_agent : GitHubAgent
        Instance of the GitHubAgent class used to create a fork.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that a ValueError is raised.
    """
    # Arrange
    github_agent.token = "test_token"
    mock_post.return_value.status_code = 400
    # Assert
    with pytest.raises(ValueError, match="Failed to create fork."):
        github_agent.create_fork()
