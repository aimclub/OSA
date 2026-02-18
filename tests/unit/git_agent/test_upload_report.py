from unittest.mock import call, mock_open, patch

import pytest
from git import GitCommandError


@patch("builtins.open", new_callable=mock_open, read_data=b"test content")
def test_upload_report_success(mock_file, github_agent):
    """
    Test that uploading a PDF report succeeds and performs the expected Git operations.
    
    Parameters
    ----------
    mock_file
        Mock object for the built-in ``open`` function, used to verify that the
        report file is read in binary mode.
    github_agent
        Instance of the GitHub agent that handles report uploads and PR creation.
    
    Returns
    -------
    None
    """
    # Arrange
    report_filename = "test_report.pdf"
    report_filepath = "test/filepath"
    default_report_branch = "osa_tool_attachments"
    default_message = "upload pdf report"

    # Act
    github_agent.upload_report(report_filename, report_filepath)

    # Assert
    mock_file.assert_any_call(report_filepath, "rb")
    github_agent.repo.git.checkout.assert_has_calls(
        [call("-b", default_report_branch), call("-b", github_agent.branch_name)]
    )
    github_agent.repo.git.add.assert_called_once_with(".")
    github_agent.repo.git.commit.assert_called_once_with("-m", default_message)
    github_agent.repo.git.push.assert_called_once_with(
        "--set-upstream",
        "origin",
        default_report_branch,
        force_with_lease=False,
        force=True,
    )

    expected_report_url = f"{github_agent.fork_url}/blob/{default_report_branch}/{report_filename}"
    expected_pr_body = f"\nGenerated report - [{report_filename}]({expected_report_url})\n"
    assert github_agent.pr_report_body == expected_pr_body


@patch("builtins.open", new_callable=mock_open, read_data=b"test content")
def test_upload_report_custom_branch_and_message(mock_file, github_agent):
    """
    Test uploading a report to a custom branch with a custom commit message.
    
    Parameters
    ----------
    mock_file
        Mocked file object used to simulate opening a file.
    github_agent
        Instance of the GitHub agent used to perform upload operations.
    
    This test verifies that the `upload_report` method correctly:
    * Adds all files to the git index.
    * Commits with the provided custom message.
    * Pushes to the specified custom branch with force.
    * Constructs the pull request body containing a link to the uploaded report.
    
    The test asserts that the GitHub agent's internal state (`pr_report_body`) matches the expected format.
    
    Returns
    -------
    None
    """
    # Arrange
    report_filename = "custom_report.pdf"
    report_filepath = "test/filepath"
    custom_branch = "custom_branch"
    custom_message = "custom message"

    # Act
    github_agent.upload_report(
        report_filename,
        report_filepath,
        report_branch=custom_branch,
        commit_message=custom_message,
    )

    # Assert
    github_agent.repo.git.add.assert_called_once_with(".")
    github_agent.repo.git.commit.assert_called_once_with("-m", custom_message)
    github_agent.repo.git.push.assert_called_once_with(
        "--set-upstream", "origin", custom_branch, force_with_lease=False, force=True
    )

    expected_report_url = f"{github_agent.fork_url}/blob/{custom_branch}/{report_filename}"
    expected_pr_body = f"\nGenerated report - [{report_filename}]({expected_report_url})\n"
    assert github_agent.pr_report_body == expected_pr_body


@patch("builtins.open", new_callable=mock_open, read_data=b"test content")
def test_upload_report_existing_branch(mock_file, github_agent):
    """
    Test uploading a PDF report when the target branch already exists.
    
    This test verifies that the `GitHubAgent.upload_report` method correctly handles
    the case where the report branch already exists in the repository. It ensures
    that the report file is opened in binary mode, the repository checks out the
    existing branch, creates a new branch if necessary, stages all changes, commits
    with the appropriate message, and pushes the branch to the remote with the
    correct options.
    
    Parameters
    ----------
    mock_file : mock
        Mock object for the built-in `open` function, used to verify that the
        report file is read in binary mode.
    github_agent : GitHubAgent
        Mocked GitHubAgent instance with a repository and git command mocks.
    
    Returns
    -------
    None
    """
    # Arrange
    report_filename = "test_report.pdf"
    report_filepath = "test/filepath"
    default_report_branch = "osa_tool_attachments"
    github_agent.repo.heads = {default_report_branch: None}
    default_message = "upload pdf report"

    # Act
    github_agent.upload_report(report_filename, report_filepath)

    # Assert
    mock_file.assert_any_call(report_filepath, "rb")
    github_agent.repo.git.checkout.assert_has_calls([call(default_report_branch), call("-b", github_agent.branch_name)])
    github_agent.repo.git.add.assert_called_once_with(".")
    github_agent.repo.git.commit.assert_called_once_with("-m", default_message)
    github_agent.repo.git.push.assert_called_once_with(
        "--set-upstream",
        "origin",
        default_report_branch,
        force_with_lease=False,
        force=True,
    )
