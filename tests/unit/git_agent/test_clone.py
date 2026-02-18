from unittest.mock import MagicMock, patch

import pytest
from git import GitCommandError, InvalidGitRepositoryError


@patch("osa_tool.git_agent.git_agent.Repo")
@patch("osa_tool.git_agent.git_agent.logger")
def test_clone_repository_already_initialized(mock_logger, mock_repo, github_agent):
    """
    Test that cloning a repository that is already initialized does not attempt to
    re‑clone and logs an appropriate warning.
    
    Parameters
    ----------
    mock_logger : object
        Mocked logger used to verify that a warning is emitted.
    mock_repo : object
        Mocked Repo class used to verify that no repository cloning occurs.
    github_agent : object
        Instance of the GitHub agent under test.
    
    Returns
    -------
    None
    """
    # Act
    github_agent.clone_repository()
    # Assert
    mock_logger.warning.assert_called_once_with(f"Repository is already initialized ({github_agent.repo_url})")
    mock_repo.assert_not_called()


@patch("osa_tool.git_agent.git_agent.Repo")
@patch("osa_tool.git_agent.git_agent.logger")
@patch("osa_tool.git_agent.git_agent.os.path.exists")
def test_clone_repository_directory_exists_invalid_repo(mock_exists, mock_logger, mock_repo, github_agent):
    """
    Test that `clone_repository` raises an `InvalidGitRepositoryError` when the target
    directory already exists but is not a valid Git repository.
    
    Parameters
    ----------
    mock_exists : mock
        Mock for `os.path.exists` to simulate that the clone directory already exists.
    mock_logger : mock
        Mock for the module-level logger used by `GitHubAgent` to record error messages.
    mock_repo : mock
        Mock for the `Repo` class from `git` to raise an `InvalidGitRepositoryError`
        when attempting to instantiate a repository from the existing directory.
    github_agent : GitHubAgent
        The `GitHubAgent` instance under test, whose `repo` attribute is set to
        `None` before the test and whose `clone_repository` method is exercised.
    
    Returns
    -------
    None
        This function is a test case and does not return a value.
    """
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
    """
    Test the cloning of a new repository when no local clone exists.
    
    This test verifies that the `clone_repository` method of a `GitHubAgent` instance
    correctly initiates a clone operation when the target directory does not already
    exist. It ensures that the repository is cloned from the authenticated URL,
    that the correct branch and options are passed, and that an informational log
    message is emitted.
    
    Parameters
    ----------
    mock_exists : mock
        Mock object for `os.path.exists`, configured to return ``False`` to simulate
        a non‑existent clone directory.
    mock_logger : mock
        Mock object for the module logger, used to verify that an appropriate
        informational message is logged.
    mock_repo : mock
        Mock object for `git.Repo`, used to confirm that `clone_from` is called
        with the expected arguments.
    github_agent : GitHubAgent
        The instance of the agent under test, whose `repo` attribute is set to
        ``None`` to simulate a fresh clone scenario.
    
    Returns
    -------
    None
        This function does not return a value; it performs assertions on the
        mocked objects to validate behavior.
    """
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
        f"Cloning the {github_agent.base_branch} branch from {github_agent.repo_url} into directory {github_agent.clone_dir}..."
    )


@patch("osa_tool.git_agent.git_agent.Repo")
@patch("osa_tool.git_agent.git_agent.logger")
@patch("osa_tool.git_agent.git_agent.os.path.exists")
def test_clone_repository_clone_error(mock_exists, mock_logger, mock_repo, github_agent):
    """
    Test that `clone_repository` correctly handles a cloning error.
    
    This test verifies that when the underlying `Repo.clone_from` method raises a
    `GitCommandError`, the `clone_repository` method propagates the exception and
    logs an appropriate error message. It also ensures that the repository
    attribute is reset to `None` before attempting to clone.
    
    Parameters
    ----------
    mock_exists : mock
        Mock for `os.path.exists` to simulate that the repository path does not
        exist.
    mock_logger : mock
        Mock for the module-level logger used by the GitAgent.
    mock_repo : mock
        Mock for the `Repo` class used to simulate cloning behavior.
    github_agent : GitAgent
        Instance of the GitAgent under test.
    
    Returns
    -------
    None
    """
    # Arrange
    github_agent.repo = None
    mock_exists.return_value = False
    mock_repo.clone_from.side_effect = GitCommandError("Cloning failed", "git")
    #  Act
    with pytest.raises(GitCommandError):
        github_agent.clone_repository()
    # Assert
    mock_logger.error.assert_called_once_with("Cloning failed: GitCommandError('Cloning failed', 'git')")
