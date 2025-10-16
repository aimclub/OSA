from unittest.mock import patch

import pytest

from osa_tool.readmegen.generator.base_builder import MarkdownBuilderBase
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture
def builder(mock_config_loader, mock_sourcerank, mock_repository_metadata):
    return MarkdownBuilderBase(mock_config_loader, mock_repository_metadata)


def test_load_template_keys(builder):
    # Act
    template = builder.load_template()

    # Assert
    assert "overview" in template
    assert "installation" in template
    assert "license" in template
    assert "citation" in template


def test_load_template_file_not_found(builder):
    with patch("osa_tool.readmegen.generator.base_builder.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            builder.load_template()


def test_overview_section(builder):
    # Arrange
    builder._overview = "This is a test overview"

    # Act
    result = builder.overview

    # Assert
    assert "This is a test overview" in result
    assert result.startswith("## Overview")


def test_getting_started_section(builder):
    # Arrange
    builder._getting_started = "Run `make install`"

    # Act
    result = builder.getting_started

    # Assert
    assert "Run `make install`" in result
    assert result.startswith("## Getting Started")


def test_examples_section_with_examples(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("WITH_EXAMPLES_ONLY")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    # Act
    result = builder.examples

    # Assert
    assert "tutorials/getting_started.ipynb" in result
    assert result.startswith("## Examples")


def test_examples_section_no_examples(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    # Assert
    assert builder.examples == ""


def test_documentation_section_with_homepage(builder):
    # Act
    result = builder.documentation

    # Assert
    assert builder.metadata.homepage_url in result
    assert result.startswith("## Documentation")


def test_documentation_section_with_local_docs(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("WITH_DOCS")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.metadata.homepage_url = None

    # Act
    result = builder.documentation

    # Assert
    expected = builder.config.git.repository + "/tree/" + builder.metadata.default_branch + "/docs/"
    assert expected in result


def test_documentation_section_empty(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.metadata.homepage_url = None

    # Assert
    assert builder.documentation == ""


def test_license_section_with_file(builder):
    # Arrange
    builder.metadata.license_name = "MIT"

    # Act
    result = builder.license

    # Assert
    assert "MIT" in result
    assert "LICENSE" in result


def test_license_section_empty(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.metadata.license_name = None

    # Assert
    assert builder.license == ""


def test_citation_section_with_file(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    # Act
    result = builder.citation

    # Assert
    assert "## Citation" in result
    assert "CITATION" in result
    assert builder._template["citation_v1"].split("{")[0] in result


def test_citation_section_with_llm(builder, sourcerank_with_repo_tree, llm_client, mock_model_handler):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    llm_client.model_handler = mock_model_handler(side_effect=['{"citation": "LLM CITATION"}'])

    with patch("osa_tool.readmegen.generator.base_builder.LLMClient", return_value=llm_client):
        # Act
        result = builder.citation

    # Assert
    assert "## Citation" in result
    assert "LLM CITATION" in result


def test_citation_section_fallback(builder, sourcerank_with_repo_tree, llm_client, mock_model_handler):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    llm_client.model_handler = mock_model_handler(side_effect=['{"citation": ""}'])

    with patch("osa_tool.readmegen.generator.base_builder.LLMClient", return_value=llm_client):
        # Act
        result = builder.citation

    # Assert
    assert "## Citation" in result
    assert builder.metadata.owner in result
    assert builder.metadata.created_at.split("-")[0] in result
