import os
from unittest.mock import patch

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.docs_generator.contributing import ContributingBuilder
from tests.utils.fixtures.sourcerank import sourcerank_with_repo_tree
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_contributing_builder_initialization(mock_config_loader, load_metadata_contributing):
    # Arrange
    builder = ContributingBuilder(mock_config_loader)

    # Assert
    assert builder.repo_url == mock_config_loader.config.git.repository
    assert builder.metadata == load_metadata_contributing.return_value

    assert isinstance(builder.sourcerank, SourceRank)

    assert builder.url_path.startswith("https://")
    assert builder.url_path.endswith("/")
    assert "tree/" in builder.branch_path

    assert builder.template_path.endswith("contributing.toml")
    assert builder.file_to_save.endswith("CONTRIBUTING.md")
    assert os.path.basename(os.path.dirname(builder.file_to_save)) == ".github"
    expected_repo_path = os.path.join(os.getcwd(), builder.repo_url.split("/")[-1], ".github")
    assert builder.repo_path == expected_repo_path

    template = builder.load_template()
    assert isinstance(template, dict)
    for key in ["introduction", "guide", "before_pull_request", "acknowledgements"]:
        assert key in template

    assert builder._template == template


def test_introduction_property(mock_config_loader, load_metadata_contributing):
    # Arrange
    builder = ContributingBuilder(mock_config_loader)

    # Act
    intro_text = builder.introduction

    # Assert
    assert load_metadata_contributing.return_value.name in intro_text
    assert builder.issues_url in intro_text


def test_guide_property(mock_config_loader, load_metadata_contributing):
    # Arrange
    builder = ContributingBuilder(mock_config_loader)

    # Act
    guide_text = builder.guide

    # Assert
    assert builder.url_path in guide_text
    assert load_metadata_contributing.return_value.name in guide_text


def test_before_pr_property(mock_config_loader, load_metadata_contributing):
    # Arrange
    builder = ContributingBuilder(mock_config_loader)

    # Act
    before_pr_text = builder.before_pr

    # Assert
    assert load_metadata_contributing.return_value.name in before_pr_text
    assert builder.documentation in before_pr_text
    assert builder.readme in before_pr_text
    assert builder.tests in before_pr_text


def test_documentation_with_docs_presence_true(
    mock_config_loader, load_metadata_contributing, sourcerank_with_repo_tree
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_loader)
    builder.sourcerank = sourcerank

    # Act
    doc_section = builder.documentation

    # Assert
    assert "docs/" in doc_section or builder.metadata.homepage_url in doc_section


def test_documentation_with_docs_presence_false_and_no_homepage(
    mock_config_loader, load_metadata_contributing, sourcerank_with_repo_tree
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_loader)
    builder.sourcerank = sourcerank
    builder.metadata.homepage_url = ""

    # Act
    doc_section = builder.documentation

    # Assert
    assert doc_section == ""


def test_readme_with_readme_presence_true(mock_config_loader, load_metadata_contributing, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_loader)
    builder.sourcerank = sourcerank

    # Act
    readme_section = builder.readme

    # Assert
    assert "README" in readme_section


def test_readme_with_readme_presence_false(mock_config_loader, load_metadata_contributing, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_loader)
    builder.sourcerank = sourcerank

    # Act
    readme_section = builder.readme

    # Assert
    assert readme_section == ""


def test_tests_property_with_tests_presence(mock_config_loader, load_metadata_contributing, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_loader)
    builder.sourcerank = sourcerank

    # Act
    tests_section = builder.tests

    # Assert
    assert "tests/" in tests_section or "test" in tests_section.lower()
    assert tests_section != ""


def test_tests_property_without_tests_presence(
    mock_config_loader, load_metadata_contributing, sourcerank_with_repo_tree
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_loader)
    builder.sourcerank = sourcerank

    # Act
    tests_section = builder.tests

    # Assert
    assert tests_section == ""


def test_acknowledgements_property(mock_config_loader, load_metadata_contributing):
    # Arrange
    builder = ContributingBuilder(mock_config_loader)

    # Act
    acknowledgements = builder.acknowledgements

    # Assert
    assert isinstance(acknowledgements, str)
    assert len(acknowledgements) > 0


def test_build_creates_dir_and_saves_file(mock_config_loader, load_metadata_contributing, tmp_path, caplog):
    # Arrange
    builder = ContributingBuilder(mock_config_loader)
    builder.repo_path = tmp_path / ".github"
    builder.file_to_save = builder.repo_path / "CONTRIBUTING.md"
    caplog.set_level("INFO")

    with (
        patch("osa_tool.docs_generator.contributing.save_sections") as mock_save_sections,
        patch("osa_tool.docs_generator.contributing.remove_extra_blank_lines") as mock_remove_blank_lines,
    ):
        mock_save_sections.return_value = None
        mock_remove_blank_lines.return_value = None

        # Act
        builder.build()

        # Assert
        assert builder.repo_path.exists()
        mock_save_sections.assert_called_once()
        mock_remove_blank_lines.assert_called_once_with(builder.file_to_save)
        assert f"CONTRIBUTING.md successfully generated in folder {builder.repo_path}" in caplog.text


def test_build_handles_exception_and_logs_error(mock_config_loader, load_metadata_contributing, caplog):
    # Arrange
    builder = ContributingBuilder(mock_config_loader)
    caplog.set_level("ERROR")

    with (patch("os.path.exists", side_effect=Exception("test error")),):
        # Act
        builder.build()

        # Assert
        assert "Error while generating CONTRIBUTING.md" in caplog.text
