import pytest
from unittest.mock import patch


@patch("osa_tool.git_agent.git_agent.requests.get")
@patch("osa_tool.git_agent.git_agent.requests.put")
def test_star_repository_already_stars(mock_put, mock_get, github_agent):
    """
    Test that `star_repository` does not attempt to star a repository that is already starred.
    
    Parameters
    ----------
    mock_put : mock
        Mock object for `requests.put` patched into the module.
    mock_get : mock
        Mock object for `requests.get` patched into the module.
    github_agent : GitHubAgent
        Instance of the GitHubAgent class under test.
    
    Returns
    -------
    None
    """
    # Arrange
    github_agent.token = "test_token"
    mock_get.return_value.status_code = 204
    # Act
    github_agent.star_repository()
    # Assert
    mock_put.assert_not_called()


@patch("osa_tool.git_agent.git_agent.requests.get")
@patch("osa_tool.git_agent.git_agent.requests.put")
def test_star_repository_adds_star(mock_put, mock_get, github_agent):
    """
    Test that the GitHubAgent correctly adds a star to a repository.
    
    This test verifies that when a repository is not already starred (indicated by a 404
    response from a GET request), the `star_repository` method issues a PUT request
    to add a star. It sets a test token on the agent, configures the mocked GET and
    PUT responses, invokes the method, and asserts that the PUT request was made
    exactly once.
    
    Args:
        mock_put: Mock object for the `requests.put` function.
        mock_get: Mock object for the `requests.get` function.
        github_agent: Instance of the GitHubAgent under test.
    
    Returns:
        None
    """
    # Arrange
    github_agent.token = "test_token"
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 204
    # Act
    github_agent.star_repository()
    # Assert
    mock_put.assert_called_once()


@patch("osa_tool.git_agent.git_agent.requests.get")
@patch("osa_tool.git_agent.git_agent.requests.put")
def test_star_repository_error(mock_put, mock_get, github_agent):
    """
    Test that `GitHubAgent.star_repository` raises a `ValueError` when the
    repository cannot be starred due to HTTP errors.
    
    Parameters
    ----------
    mock_put
        Mock object for `requests.put` patched by the `@patch` decorator.
    mock_get
        Mock object for `requests.get` patched by the `@patch` decorator.
    github_agent
        Instance of `GitHubAgent` used to perform the star operation.
    
    Returns
    -------
    None
        This test function does not return a value; it verifies that a
        `ValueError` is raised when the HTTP responses indicate failure.
    """
    # Arrange
    github_agent.token = "test_token"
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 400
    # Assert
    with pytest.raises(ValueError, match="Failed to star repository."):
        github_agent.star_repository()


@patch("osa_tool.git_agent.git_agent.requests.get")
def test_star_repository_request_error(mock_get, github_agent):
    """
    Test that the GitHubAgent raises a ValueError when the star repository request fails.
    
    Parameters
    ----------
    mock_get
        Mock object for the `requests.get` function, provided by the `@patch` decorator.
    github_agent
        Instance of the GitHubAgent class used in the test.
    
    Returns
    -------
    None
    """
    # Arrange
    github_agent.token = "test_token"
    mock_get.return_value.status_code = 500
    # Assert
    with pytest.raises(ValueError, match="Failed to check star status."):
        github_agent.star_repository()
