import json
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
    overview_data = {"overview": "This is a test overview"}
    builder._overview_json = json.dumps(overview_data)

    # Act
    result = builder.overview

    # Assert
    assert "This is a test overview" in result
    assert result.startswith("## Overview")


def test_getting_started_section(builder):
    # Arrange
    getting_started_data = {"getting_started": "Run `make install`"}
    builder._getting_started_json = json.dumps(getting_started_data)

    # Act
    result = builder.getting_started

    # Assert
    assert "Run `make install`" in result
    assert result.startswith("## Getting Started")


def test_examples_section_with_examples(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("WITH_EXAMPLES_ONLY")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.sourcerank = sourcerank

    # Act
    result = builder.examples

    # Assert
    assert "tutorials/getting_started.ipynb" in result
    assert result.startswith("## Examples")


def test_examples_section_no_examples(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.sourcerank = sourcerank

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
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.sourcerank = sourcerank
    builder.metadata.homepage_url = None

    # Act
    result = builder.documentation

    # Assert
    expected = builder.config.git.repository + "/tree/" + builder.metadata.default_branch + "/docs/"
    assert expected in result


def test_documentation_section_empty(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.sourcerank = sourcerank
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
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.sourcerank = sourcerank
    builder.metadata.license_name = None

    # Assert
    assert builder.license == ""


def test_citation_section_with_file(builder):
    # Act
    result = builder.citation

    # Assert
    assert "## Citation" in result


def test_citation_section_without_file(builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.sourcerank = sourcerank

    # Act
    result = builder.citation

    # Assert
    assert "## Citation" in result
    assert builder.metadata.owner in result
    assert builder.metadata.created_at.split("-")[0] in result


def test_deduplicate_sections_skips_if_no_installation(builder):
    # Arrange
    builder.installation = ""
    builder._getting_started_json = json.dumps({"getting_started": "Run this"})

    # Act
    builder.deduplicate_sections()

    # Assert
    assert builder.installation == ""
    assert json.loads(builder._getting_started_json)["getting_started"] == "Run this"


def test_deduplicate_sections_skips_if_no_getting_started(builder):
    # Arrange
    builder.installation = "Some installation instructions"
    builder._getting_started_json = json.dumps({"getting_started": ""})

    # Act
    builder.deduplicate_sections()

    # Assert
    assert builder.installation == "Some installation instructions"
    assert json.loads(builder._getting_started_json)["getting_started"] == ""


def test_deduplicate_sections_calls_llm_and_updates(builder):
    # Arrange
    builder.installation = "Install A"
    builder._getting_started_json = json.dumps({"getting_started": "Run A"})

    mock_response = {"installation": "Install A deduped", "getting_started": "Run A deduped"}
    with patch("osa_tool.readmegen.generator.base_builder.LLMClient") as MockLLM:
        instance = MockLLM.return_value
        instance.deduplicate_sections.return_value = json.dumps(mock_response)

        # Act
        builder.deduplicate_sections()

    # Assert
    instance.deduplicate_sections.assert_called_once_with("Install A", "Run A")
    assert builder.installation == "Install A deduped"
    assert json.loads(builder._getting_started_json)["getting_started"] == "Run A deduped"


def test_deduplicate_sections_handles_empty_installation(builder):
    # Arrange
    builder.installation = "Install B"
    builder._getting_started_json = json.dumps({"getting_started": "Run B"})

    mock_response = {"installation": "", "getting_started": "Install B deduped"}
    with patch("osa_tool.readmegen.generator.base_builder.LLMClient") as MockLLM:
        instance = MockLLM.return_value
        instance.deduplicate_sections.return_value = json.dumps(mock_response)

        # Act
        builder.deduplicate_sections()

    # Assert
    assert builder.installation == ""
    assert json.loads(builder._getting_started_json)["getting_started"] == "Install B deduped"
