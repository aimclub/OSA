from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.operations.docs.readme_generation.pipeline.nodes.deterministic_builder import _DeterministicSections


def _make_builder(mock_config_manager, mock_repository_metadata):
    """Construct _DeterministicSections with a minimal mocked ReadmeContext."""
    context = MagicMock()
    context.config_manager = mock_config_manager
    context.metadata = mock_repository_metadata
    with patch("osa_tool.operations.docs.readme_generation.pipeline.nodes.deterministic_builder.SourceRank"):
        builder = _DeterministicSections(context)
    builder._sr = MagicMock()
    builder._sr.citation_presence.return_value = False
    builder._sr.tree = ""
    return builder, context


def test_citation_fallback_uses_created_at_year(mock_config_manager, mock_repository_metadata):
    # Arrange - metadata has a valid ISO created_at
    mock_repository_metadata.created_at = "2021-04-15T10:00:00Z"
    mock_repository_metadata.owner = "testowner"
    builder, context = _make_builder(mock_config_manager, mock_repository_metadata)
    builder._extract_citation_from_readme = MagicMock(return_value="")

    # Act
    content = builder.citation()

    # Assert
    assert "2021" in content
    assert "testowner" in content


def test_citation_fallback_year_when_created_at_empty(mock_config_manager, mock_repository_metadata):
    # Arrange - SourceCraft doesn't return created_at
    mock_repository_metadata.created_at = ""
    builder, context = _make_builder(mock_config_manager, mock_repository_metadata)
    builder._extract_citation_from_readme = MagicMock(return_value="")

    # Act
    content = builder.citation()

    # Assert
    current_year = str(datetime.now().year)
    assert f"year = {{{current_year}}}" in content
    assert "year = {}" not in content


def test_citation_fallback_year_when_created_at_none(mock_config_manager, mock_repository_metadata):
    # Arrange
    mock_repository_metadata.created_at = None
    builder, context = _make_builder(mock_config_manager, mock_repository_metadata)
    builder._extract_citation_from_readme = MagicMock(return_value="")

    # Act
    content = builder.citation()

    # Assert
    current_year = str(datetime.now().year)
    assert current_year in content
    assert "year = {}" not in content


def test_citation_url_has_no_git_suffix(mock_config_manager, mock_repository_metadata):
    # Arrange
    mock_repository_metadata.created_at = "2022-01-01T00:00:00Z"
    builder, context = _make_builder(mock_config_manager, mock_repository_metadata)
    builder._extract_citation_from_readme = MagicMock(return_value="")
    repo_url = mock_config_manager.get_git_settings().repository

    # Act
    content = builder.citation()

    # Assert
    assert f"{repo_url}.git" not in content
    assert repo_url in content


def test_local_citation_fallback_uses_placeholder_instead_of_absolute_path(
    mock_config_manager, mock_repository_metadata, tmp_path
):
    repo_dir = tmp_path / "local_test_repo"
    repo_dir.mkdir()
    mock_config_manager.config.git.repository = repo_dir
    mock_config_manager.config.git.host = None
    mock_config_manager.config.git.host_domain = None
    mock_config_manager.config.git.full_name = "local/local_test_repo"
    mock_repository_metadata.clone_url_http = ""
    mock_repository_metadata.created_at = "2024-01-01T00:00:00Z"

    builder, _ = _make_builder(mock_config_manager, mock_repository_metadata)
    builder._extract_citation_from_readme = MagicMock(return_value="")

    content = builder.citation()

    assert "REPOSITORY_URL" in content
    assert str(repo_dir) not in content


def test_local_contributing_section_points_to_issue_template(mock_config_manager, mock_repository_metadata, tmp_path):
    repo_dir = tmp_path / "local_test_repo"
    repo_dir.mkdir()
    mock_config_manager.config.git.repository = repo_dir
    mock_config_manager.config.git.host = None
    mock_config_manager.config.git.host_domain = None
    mock_repository_metadata.clone_url_http = ""
    mock_repository_metadata.issues_url = ""

    builder, _ = _make_builder(mock_config_manager, mock_repository_metadata)
    builder._sr.contributing_presence.return_value = True

    content = builder.contributing()

    assert ".github/ISSUE_TEMPLATE/BUG_ISSUE.md" in content
    assert ".github/CONTRIBUTING.md" in content


def test_contributing_strips_issue_url_template_suffix(mock_config_manager, mock_repository_metadata):
    mock_repository_metadata.issues_url = "https://api.github.com/repos/owner/repo/issues{/number}"

    builder, _ = _make_builder(mock_config_manager, mock_repository_metadata)
    builder._sr.contributing_presence.return_value = False

    content = builder.contributing()

    assert "issues{/number}" not in content
    assert "https://api.github.com/repos/owner/repo/issues" in content
