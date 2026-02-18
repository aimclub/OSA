from unittest.mock import patch

import pytest


@patch("osa_tool.git_agent.git_agent.requests.post")
@patch("osa_tool.git_agent.git_agent.logger")
def test_create_pull_request_success(mock_logger, mock_post, github_agent):
    """
    test_create_pull_request_success
    
        Tests that the GitHubAgent correctly creates a pull request when the
        GitHub API returns a successful response. The test verifies that the
        POST request is made with the expected payload and headers, and that
        a success message is logged with the pull request URL.
    
        Parameters
        ----------
        mock_logger
            Mock object replacing the module-level logger used by the agent.
        mock_post
            Mock object replacing `requests.post` to simulate GitHub API
            responses.
        github_agent
            Instance of the GitHubAgent class under test.
    
        Returns
        -------
        None
    """
    # Arrange
    mock_post.return_value.status_code = 201
    mock_post.return_value.json.return_value = {"html_url": "https://github.com/testuser/testrepo/pull/1"}
    # Act
    github_agent.create_pull_request()
    # Assert
    mock_post.assert_called_once_with(
        "https://api.github.com/repos/testuser/testrepo/pulls",
        json={
            "title": "Initial commit",
            "head": "testuser:feature-branch",
            "base": "main",
            "body": "Initial commit" + github_agent.AGENT_SIGNATURE,
            "maintainer_can_modify": True,
        },
        headers={
            "Authorization": "token test_token",
            "Accept": "application/vnd.github.v3+json",
        },
    )
    mock_logger.info.assert_called_once_with(
        "GitHub pull request created successfully: https://github.com/testuser/testrepo/pull/1"
    )


@patch("osa_tool.git_agent.git_agent.requests.post")
@patch("osa_tool.git_agent.git_agent.logger")
def test_create_pull_request_error(mock_logger, mock_post, github_agent):
    """
    Test that creating a pull request raises a ValueError when the HTTP request fails.
    
    This test configures the mocked `requests.post` to return a 400 status code and a
    "Bad Request" message. It then verifies that calling `github_agent.create_pull_request()`
    raises a `ValueError` with the expected message and that the logger records the
    error details.
    
    Parameters
    ----------
    mock_logger : mock
        Mocked logger used by the GitHub agent.
    mock_post : mock
        Mocked `requests.post` function that simulates the HTTP response.
    github_agent : GitHubAgent
        Instance of the GitHub agent under test.
    
    Returns
    -------
    None
    """
    # Arrange
    mock_post.return_value.status_code = 400
    mock_post.return_value.text = "Bad Request"
    # Act
    with pytest.raises(ValueError, match="Failed to create pull request."):
        github_agent.create_pull_request()
    # Assert
    mock_logger.error.assert_called_once_with("Failed to create pull request: 400 - Bad Request")


@patch("osa_tool.git_agent.git_agent.requests.post")
@patch("osa_tool.git_agent.git_agent.logger")
def test_create_pull_request_already_exists(mock_logger, mock_post, github_agent):
    """
    Test that attempting to create a pull request when one already exists
    results in an error being logged.
    
    Parameters
    ----------
    mock_logger : mock
        Mocked logger object patched into the module.
    mock_post : mock
        Mocked requests.post function patched into the module.
    github_agent : GitHubAgent
        Instance of the GitHubAgent class under test.
    
    Returns
    -------
    None
    """
    # Arrange
    mock_post.return_value.status_code = 422
    mock_post.return_value.text = "pull request already exists"
    # Act
    github_agent.create_pull_request()
    #  Assert
    mock_logger.error.assert_called_once_with("Failed to create pull request: 422 - pull request already exists")
