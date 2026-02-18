from unittest.mock import MagicMock, call, patch


@patch("osa_tool.git_agent.git_agent.logger")
def test_create_and_checkout_branch_exists(mock_logger, github_agent):
    """
    Test that the GitHub agent correctly handles the case where the target branch already exists.
    
    Parameters
    ----------
    mock_logger : object
        Mocked logger instance used to verify logging output.
    github_agent : object
        Mocked GitHub agent with a repository and branch handling logic.
    
    Returns
    -------
    None
    """
    # Arrange
    github_agent.repo.heads = {"feature-branch": MagicMock()}
    # Act
    github_agent.create_and_checkout_branch()
    # Assert
    github_agent.repo.git.checkout.assert_called_with("feature-branch")
    mock_logger.info.assert_called_with("Branch feature-branch already exists. Switching to it...")


@patch("osa_tool.git_agent.git_agent.logger")
def test_create_and_checkout_branch_new(mock_logger, github_agent):
    """
    Test the creation and checkout of a new branch using the GitHubAgent.
    
    This test verifies that the `create_and_checkout_branch` method:
    - Calls the repository's `git.checkout` with the correct arguments to create a new branch.
    - Logs the appropriate informational messages before and after the checkout.
    
    Parameters
    ----------
    mock_logger : object
        Mocked logger instance used to assert logging calls.
    github_agent : object
        Instance of the GitHubAgent under test, with its `repo` and `branch_name` attributes.
    
    Returns
    -------
    None
    """
    # Arrange
    github_agent.repo.heads = {}
    # Act
    github_agent.create_and_checkout_branch()
    # Assert
    github_agent.repo.git.checkout.assert_called_with("-b", github_agent.branch_name)
    mock_logger.info.assert_has_calls(
        [
            call(f"Creating and switching to branch {github_agent.branch_name}..."),
            call(f"Switched to branch {github_agent.branch_name}."),
        ]
    )
