from unittest.mock import MagicMock, patch

import pytest
from git import GitCommandError, InvalidGitRepositoryError


@patch("osa_tool.git_agent.git_agent.Repo")
@patch("osa_tool.git_agent.git_agent.logger")
def test_clone_repository_already_initialized(mock_logger, mock_repo, github_agent):
    # Act
    github_agent.clone_repository()
    # Assert
    mock_logger.warning.assert_called_once_with(f"Repository is already initialized ({github_agent.repo_url})")
    mock_repo.assert_not_called()


@patch("osa_tool.git_agent.git_agent.Repo")
@patch("osa_tool.git_agent.git_agent.logger")
@patch("osa_tool.git_agent.git_agent.os.path.exists")
def test_clone_repository_directory_exists_invalid_repo(mock_exists, mock_logger, mock_repo, github_agent):
    # Arrange
    github_agent.repo = None
    mock_exists.return_value = True
    mock_repo.side_effect = InvalidGitRepositoryError("Not a git repo")
    # Act
    with pytest.raises(InvalidGitRepositoryError):
        github_agent.clone_repository()
    # Assert
    mock_logger.error.assert_called_once_with(
        f"Directory {github_agent.clone_dir} exists but is not a valid Git repository"
    )


@patch("osa_tool.git_agent.git_agent.Repo")
@patch("osa_tool.git_agent.git_agent.logger")
@patch("osa_tool.git_agent.git_agent.os.path.exists")
def test_clone_repository_clone_new_repo(mock_exists, mock_logger, mock_repo, github_agent):
    # Arrange
    github_agent.repo = None
    mock_exists.return_value = False
    mock_repo.clone_from.return_value = MagicMock()
    # Act
    github_agent.clone_repository()
    # Assert
    mock_repo.clone_from.assert_called_once_with(
        url=github_agent._get_auth_url(),
        to_path=github_agent.clone_dir,
        branch=github_agent.base_branch,
        single_branch=True,
    )
    mock_logger.info.assert_any_call(
        f"Cloning the '{github_agent.base_branch}' branch from {github_agent.repo_url} into directory {github_agent.clone_dir}..."
    )


@patch("osa_tool.git_agent.git_agent.Repo")
@patch("osa_tool.git_agent.git_agent.logger")
@patch("osa_tool.git_agent.git_agent.os.path.exists")
def test_clone_repository_clone_error(mock_exists, mock_logger, mock_repo, github_agent):
    # Arrange
    github_agent.repo = None
    mock_exists.return_value = False
    mock_repo.clone_from.side_effect = GitCommandError("Cloning failed", "git")
    #  Act
    with pytest.raises(SystemExit):
        github_agent.clone_repository()
    # Assert
    calls = [call.args[0] for call in mock_logger.error.call_args_list]
    assert any("Cloning failed" in msg for msg in calls)
