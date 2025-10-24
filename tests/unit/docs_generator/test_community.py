import os
from unittest.mock import patch

import pytest

from osa_tool.docs_generator.community import CommunityTemplateBuilder
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture(autouse=True)
def mock_os_makedirs():
    with patch("osa_tool.docs_generator.community.os.makedirs"):
        yield


def test_community_template_builder_init(
    mock_config_loader,
    mock_repository_metadata,
):
    # Act
    builder = CommunityTemplateBuilder(mock_config_loader, mock_repository_metadata)

    # Assert
    assert builder.repo_url == mock_config_loader.config.git.repository
    assert builder.metadata == mock_repository_metadata
    assert builder.sourcerank is not None
    assert "code_of_conduct" in builder._template
    assert "pull_request" in builder._template
    assert "docs_issue" in builder._template
    assert "feature_issue" in builder._template
    assert "bug_issue" in builder._template

    assert builder.repo_path.endswith(f".{mock_config_loader.config.git.host}")
    assert builder.code_of_conduct_to_save.endswith("CODE_OF_CONDUCT.md")
    if "github" in mock_config_loader.config.git.host:
        assert builder.pr_to_save.endswith("PULL_REQUEST_TEMPLATE.md")
    elif "gitlab" in mock_config_loader.config.git.host:
        assert builder.pr_to_save.endswith("MERGE_REQUEST_TEMPLATE.md")
    assert builder.docs_issue_to_save.endswith("DOCUMENTATION_ISSUE.md")
    assert builder.feature_issue_to_save.endswith("FEATURE_ISSUE.md")
    assert builder.bug_issue_to_save.endswith("BUG_ISSUE.md")


def test_build_code_of_conduct(mock_config_loader, mock_repository_metadata, tmp_path, caplog):
    # Arrange
    builder = CommunityTemplateBuilder(mock_config_loader, mock_repository_metadata)
    builder.repo_path = tmp_path / f".{mock_config_loader.config.git.host}"
    builder.code_of_conduct_to_save = builder.repo_path / "CODE_OF_CONDUCT.md"
    caplog.set_level("INFO")

    with patch("osa_tool.docs_generator.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_code_of_conduct()

        # Assert
        mock_save_sections.assert_called_once()
        assert f"CODE_OF_CONDUCT.md successfully generated in folder {builder.repo_path}" in caplog.text


def test_build_pull_request(mock_config_loader, mock_repository_metadata, sourcerank_with_repo_tree, tmp_path, caplog):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = CommunityTemplateBuilder(mock_config_loader, mock_repository_metadata)
    builder.sourcerank = sourcerank
    builder.repo_path = tmp_path / f".{mock_config_loader.config.git.host}"
    if "github" in mock_config_loader.config.git.host:
        builder.pr_to_save = builder.repo_path / "PULL_REQUEST_TEMPLATE.md"
    else:
        builder.pr_to_save = builder.repo_path / "MERGE_REQUEST_TEMPLATE.md"
    caplog.set_level("INFO")

    with patch("osa_tool.docs_generator.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_pull_request()

        # Assert
        mock_save_sections.assert_called_once()
        assert (
            f"PULL_REQUEST_TEMPLATE.md successfully generated in folder {os.path.dirname(builder.pr_to_save)}"
            in caplog.text
        )


def test_build_documentation_issue_with_docs_present(
    mock_config_loader, mock_repository_metadata, sourcerank_with_repo_tree, tmp_path, caplog
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = CommunityTemplateBuilder(mock_config_loader, mock_repository_metadata)
    builder.sourcerank = sourcerank
    builder.repo_path = tmp_path / f".{mock_config_loader.config.git.host}"
    builder.docs_issue_to_save = builder.repo_path / "DOCUMENTATION_ISSUE.md"
    caplog.set_level("INFO")

    with patch("osa_tool.docs_generator.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_documentation_issue()

        # Assert
        mock_save_sections.assert_called_once()
        assert "DOCUMENTATION_ISSUE.md successfully generated in folder" in caplog.text


def test_build_documentation_issue_without_docs_present(
    mock_config_loader, mock_repository_metadata, sourcerank_with_repo_tree, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = CommunityTemplateBuilder(mock_config_loader, mock_repository_metadata)
    builder.sourcerank = sourcerank
    builder.repo_path = tmp_path / f".{mock_config_loader.config.git.host}"
    builder.docs_issue_to_save = builder.repo_path / "DOCUMENTATION_ISSUE.md"

    with patch("osa_tool.docs_generator.community.save_sections") as mock_save_sections:
        # Act
        builder.build_documentation_issue()

        # Assert
        mock_save_sections.assert_not_called()


def test_build_feature_issue(mock_config_loader, mock_repository_metadata, tmp_path, caplog):
    # Arrange
    builder = CommunityTemplateBuilder(mock_config_loader, mock_repository_metadata)
    builder.repo_path = tmp_path / f".{mock_config_loader.config.git.host}"
    builder.feature_issue_to_save = builder.repo_path / "FEATURE_ISSUE.md"
    caplog.set_level("INFO")

    with patch("osa_tool.docs_generator.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_feature_issue()

        # Assert
        mock_save_sections.assert_called_once()
        assert "FEATURE_ISSUE.md successfully generated in folder" in caplog.text


def test_build_bug_issue(mock_config_loader, mock_repository_metadata, tmp_path, caplog):
    # Arrange
    builder = CommunityTemplateBuilder(mock_config_loader, mock_repository_metadata)
    builder.repo_path = tmp_path / f".{mock_config_loader.config.git.host}"
    builder.bug_issue_to_save = builder.repo_path / "BUG_ISSUE.md"
    caplog.set_level("INFO")

    with patch("osa_tool.docs_generator.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_bug_issue()

        # Assert
        mock_save_sections.assert_called_once()
        assert "BUG_ISSUE.md successfully generated in folder" in caplog.text


@pytest.mark.parametrize(
    "method_name, expected_log",
    [
        ("build_code_of_conduct", "Error while generating CODE_OF_CONDUCT.md"),
        ("build_pull_request", "Error while generating PULL_REQUEST_TEMPLATE.md"),
        ("build_documentation_issue", "Error while generating DOCUMENTATION_ISSUE.md"),
        ("build_feature_issue", "Error while generating FEATURE_ISSUE.md"),
        ("build_bug_issue", "Error while generating BUG_ISSUE.md"),
    ],
)
def test_builder_methods_log_errors_on_exception(
    method_name, expected_log, mock_config_loader, mock_repository_metadata, sourcerank_with_repo_tree, caplog
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = CommunityTemplateBuilder(mock_config_loader, mock_repository_metadata)
    builder.sourcerank = sourcerank
    caplog.set_level("ERROR")

    with patch("osa_tool.docs_generator.community.save_sections", side_effect=Exception("save failed")):
        # Act
        method = getattr(builder, method_name)
        method()

        # Assert
        assert any(
            expected_log in message for message in caplog.messages
        ), f"Expected log message '{expected_log}' not found in logs: {caplog.messages}"
