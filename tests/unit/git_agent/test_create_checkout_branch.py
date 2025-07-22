from unittest.mock import MagicMock, call, patch


@patch("osa_tool.git_agent.git_agent.logger")
def test_create_and_checkout_branch_exists(mock_logger, github_agent):
    # Arrange
    github_agent.repo.heads = {"feature-branch": MagicMock()}
    # Act
    github_agent.create_and_checkout_branch()
    # Assert
    github_agent.repo.git.checkout.assert_called_with("feature-branch")
    mock_logger.info.assert_called_with("Branch feature-branch already exists. Switching to it...")


@patch("osa_tool.git_agent.git_agent.logger")
def test_create_and_checkout_branch_new(mock_logger, github_agent):
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
