import pytest
from unittest.mock import patch, MagicMock


def test_commit_and_push_changes_success(github_agent):
    # Arrange
    with (
        patch.object(
            github_agent, "_get_auth_url", return_value="https://auth-url.com"
        ) as mock_auth_url,
        patch("osa_tool.github_agent.github_agent.logger") as mock_logger,
    ):
        github_agent.repo.git.add = MagicMock()
        github_agent.repo.git.commit = MagicMock()
        github_agent.repo.git.remote = MagicMock()
        github_agent.repo.git.push = MagicMock()
        # Act
        github_agent.commit_and_push_changes(commit_message="Test commit")
    # Assert
    github_agent.repo.git.add.assert_called_once_with(".")
    github_agent.repo.git.commit.assert_called_once_with("-m", "Test commit")
    github_agent.repo.git.push.assert_called_once_with(
        "--set-upstream", "origin", "feature-branch", force_with_lease=True
    )
    mock_logger.info.assert_any_call("Committing changes...")
    mock_logger.info.assert_any_call("Commit completed.")
    mock_logger.info.assert_any_call(
        "Pushing changes to branch feature-branch in fork..."
    )
    mock_logger.info.assert_any_call("Push completed.")


def test_commit_and_push_changes_no_fork_url(github_agent):
    # Arrange
    github_agent.fork_url = None
    # Assert
    with pytest.raises(
        ValueError, match="Fork URL is not set. Please create a fork first."
    ):
        github_agent.commit_and_push_changes()
