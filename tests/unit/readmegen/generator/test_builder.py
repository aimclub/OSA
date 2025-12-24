import json
from unittest.mock import patch

from osa_tool.operations.docs.readme_generation.generator.builder import MarkdownBuilder
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_core_features_with_critical_features(mock_markdown_builder):
    # Arrange
    core_features_json = [
        {"feature_name": "Feature 1", "feature_description": "Description 1", "is_critical": True},
        {"feature_name": "Feature 2", "feature_description": "Description 2", "is_critical": False},
    ]

    builder = mock_markdown_builder(
        core_features=core_features_json, overview="Test overview", getting_started="Test getting started"
    )

    # Act
    result = builder.core_features

    # Assert
    assert "Feature 1" in result
    assert "Description 1" in result
    assert "Feature 2" not in result
    assert "**Feature 1**" in result


def test_core_features_no_critical_features(mock_markdown_builder):
    # Arrange
    core_features_json = [{"feature_name": "Feature 1", "feature_description": "Description 1", "is_critical": False}]
    builder = mock_markdown_builder(
        core_features=core_features_json, overview="Test overview", getting_started="Test getting started"
    )

    # Act
    result = builder.core_features

    # Assert
    assert "_No critical features identified._" in result


def test_core_features_empty_json(mock_markdown_builder):
    # Arrange
    builder = mock_markdown_builder(
        core_features=None, overview="Test overview", getting_started="Test getting started"
    )

    # Act
    result = builder.core_features

    # Assert
    assert result == ""


def test_core_features_multiple_critical_features(mock_markdown_builder):
    # Arrange
    core_features_json = [
        {"feature_name": "Feature 1", "feature_description": "Description 1", "is_critical": True},
        {"feature_name": "Feature 2", "feature_description": "Description 2", "is_critical": True},
        {"feature_name": "Feature 3", "feature_description": "Description 3", "is_critical": False},
    ]
    builder = mock_markdown_builder(
        core_features=core_features_json, overview="Test overview", getting_started="Test getting started"
    )

    # Act
    result = builder.core_features

    # Assert
    assert "1. **Feature 1**: Description 1" in result
    assert "2. **Feature 2**: Description 2" in result
    assert "Feature 3" not in result


def test_contributing_with_discussions_and_contributing_file(mock_markdown_builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = mock_markdown_builder(
        core_features="[]", overview="Test overview", getting_started="Test getting started"
    )
    builder.sourcerank = sourcerank

    with patch.object(MarkdownBuilder, "_check_url") as mock_check_url:
        mock_check_url.side_effect = lambda url: "discussions" in url

        # Act
        result = builder.contributing

    # Assert
    assert isinstance(result, str)


def test_contributing_without_discussions(mock_markdown_builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = mock_markdown_builder(
        core_features="[]", overview="Test overview", getting_started="Test getting started"
    )
    builder.sourcerank = sourcerank
    with patch.object(MarkdownBuilder, "_check_url") as mock_check_url:
        mock_check_url.return_value = False

        # Act
        result = builder.contributing

    # Assert
    assert isinstance(result, str)


def test_contributing_without_contributing_file(mock_markdown_builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = mock_markdown_builder(
        core_features="[]", overview="Test overview", getting_started="Test getting started"
    )
    builder.sourcerank = sourcerank

    with patch.object(MarkdownBuilder, "_check_url") as mock_check_url:
        mock_check_url.side_effect = lambda url: "discussions" in url

        result = builder.contributing

    # Assert
    assert isinstance(result, str)


def test_contributing_with_contributing_only(mock_markdown_builder, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("WITH_CONTRIBUTING_ONLY")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = mock_markdown_builder(
        core_features="[]", overview="Test overview", getting_started="Test getting started"
    )
    builder.sourcerank = sourcerank

    with patch.object(MarkdownBuilder, "_check_url") as mock_check_url:
        mock_check_url.return_value = True

        # Act
        result = builder.contributing

    # Assert
    assert isinstance(result, str)


def test_toc_generation(mock_markdown_builder, llm_client, mock_model_handler):
    # Arrange
    core_features_json = json.dumps([{"feature_name": "Test", "feature_description": "Desc", "is_critical": True}])
    builder = mock_markdown_builder(
        core_features=core_features_json,
        overview=None,
        getting_started="Test getting started",
    )

    llm_client.model_handler = mock_model_handler(side_effect=['{"citation": null}'])

    with patch("osa_tool.operations.docs.readme_generation.generator.base_builder.LLMClient", return_value=llm_client):

        # Act
        result = builder.toc

    # Assert
    assert isinstance(result, str)
    assert "- [" in result or "* [" in result
    assert "Getting Started" in result
    assert "Citation" in result


def test_build_method_full(mock_markdown_builder, sourcerank_with_repo_tree):
    # Arrange
    core_features_json = json.dumps(
        [{"feature_name": "Feature 1", "feature_description": "Description 1", "is_critical": True}]
    )
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = mock_markdown_builder(
        core_features=core_features_json,
        overview="Test overview",
        getting_started="Test getting started",
    )
    builder.sourcerank = sourcerank

    with patch.object(MarkdownBuilder, "_check_url", return_value=True):

        # Act
        result = builder.build()

    # Assert
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_method_minimal(mock_markdown_builder, sourcerank_with_repo_tree, llm_client, mock_model_handler):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = mock_markdown_builder(
        core_features=None,
        overview="",
        getting_started="",
    )
    builder.sourcerank = sourcerank

    llm_client.model_handler = mock_model_handler(side_effect=['{"citation": ""}'])

    with (
        patch("osa_tool.operations.docs.readme_generation.generator.base_builder.LLMClient", return_value=llm_client),
        patch.object(MarkdownBuilder, "_check_url", return_value=False),
    ):
        # Act
        result = builder.build()

    # Assert
    assert isinstance(result, str)
    assert "Getting Started" not in result
    assert "## Citation" in result
