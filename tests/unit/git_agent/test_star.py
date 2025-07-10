import pytest
from unittest.mock import patch


@patch("osa_tool.git_agent.git_agent.requests.get")
@patch("osa_tool.git_agent.git_agent.requests.put")
def test_star_repository_already_stars(mock_put, mock_get, github_agent):
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
    # Arrange
    github_agent.token = "test_token"
    mock_get.return_value.status_code = 404
    mock_put.return_value.status_code = 400
    # Assert
    with pytest.raises(ValueError, match="Failed to star repository."):
        github_agent.star_repository()


@patch("osa_tool.git_agent.git_agent.requests.get")
def test_star_repository_request_error(mock_get, github_agent):
    # Arrange
    github_agent.token = "test_token"
    mock_get.return_value.status_code = 500
    # Assert
    with pytest.raises(ValueError, match="Failed to check star status."):
        github_agent.star_repository()
