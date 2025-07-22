from unittest.mock import patch

import pytest


@patch("osa_tool.git_agent.git_agent.requests.post")
@patch("osa_tool.git_agent.git_agent.logger")
def test_create_pull_request_success(mock_logger, mock_post, github_agent):
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
    # Arrange
    mock_post.return_value.status_code = 422
    mock_post.return_value.text = "pull request already exists"
    # Act
    github_agent.create_pull_request()
    #  Assert
    mock_logger.error.assert_called_once_with("Failed to create pull request: 422 - pull request already exists")
