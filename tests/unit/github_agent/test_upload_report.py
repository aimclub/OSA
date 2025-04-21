from unittest.mock import call, patch

import pytest


@patch("osa_tool.github_agent.github_agent.logger")
def test_upload_report_success(mock_logger, github_agent):
    # Arrange
    report_filename = "test_report.pdf"
    report_branch = "osa_tool_attachments"
    commit_message = "upload pdf report"

    # Act
    github_agent.upload_report(report_filename)

    # Assert
    github_agent.repo.git.checkout.assert_has_calls([
        call('-b', report_branch),
        call('-b', github_agent.branch_name)
    ])

    expected_report_url = f"{github_agent.fork_url}/blob/{report_branch}/{report_filename}"
    expected_pr_body = f"\nGenerated report - [{report_filename}]({expected_report_url})\n"
    assert github_agent.pr_report_body == expected_pr_body


@patch("osa_tool.github_agent.github_agent.logger")
def test_upload_report_custom_branch_and_message(mock_logger, github_agent):
    # Arrange
    report_filename = "custom_report.pdf"
    custom_branch = "custom_branch"
    custom_message = "custom message"

    # Act
    github_agent.upload_report(
        report_filename,
        report_branch=custom_branch,
        commit_message=custom_message
    )

    # Assert
    github_agent.repo.git.checkout.assert_has_calls([
        call('-b', custom_branch),
        call('-b', github_agent.branch_name)
    ])

    expected_report_url = f"{github_agent.fork_url}/blob/{custom_branch}/{report_filename}"
    expected_pr_body = f"\nGenerated report - [{report_filename}]({expected_report_url})\n"
    assert github_agent.pr_report_body == expected_pr_body


@patch("osa_tool.github_agent.github_agent.logger")
def test_upload_report_existing_branch(mock_logger, github_agent):
    # Arrange
    report_filename = "test_report.pdf"
    report_branch = "osa_tool_attachments"
    github_agent.repo.heads = {report_branch: None}

    # Act
    github_agent.upload_report(report_filename)

    # Assert
    github_agent.repo.git.checkout.assert_has_calls([
        call(report_branch),
        call('-b', github_agent.branch_name)
    ])
