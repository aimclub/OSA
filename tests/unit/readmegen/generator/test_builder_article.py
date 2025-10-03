import json
from unittest.mock import patch

from osa_tool.readmegen.generator.builder_article import MarkdownBuilderArticle
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_content_section(mock_markdown_builder_article):
    # Arrange
    content_json = json.dumps({"content": "This is the content section"})
    builder = mock_markdown_builder_article(
        overview=json.dumps({"overview": "Test overview"}),
        content=content_json,
        algorithms=json.dumps({"algorithms": "Test algorithms"}),
        getting_started=json.dumps({"getting_started": "Test getting started"}),
    )

    # Act
    result = builder.content

    # Assert
    assert isinstance(result, str)


def test_content_empty_json(mock_markdown_builder_article):
    # Arrange
    builder = mock_markdown_builder_article(
        overview=json.dumps({"overview": "Test overview"}),
        content=None,
        algorithms=json.dumps({"algorithms": "Test algorithms"}),
        getting_started=json.dumps({"getting_started": "Test getting started"}),
    )

    # Act
    result = builder.content

    # Assert
    assert result == ""


def test_algorithms_section(mock_markdown_builder_article):
    # Arrange
    algorithms_json = json.dumps({"algorithms": "These are the algorithms"})
    builder = mock_markdown_builder_article(
        overview=json.dumps({"overview": "Test overview"}),
        content=json.dumps({"content": "Test content"}),
        algorithms=algorithms_json,
        getting_started=json.dumps({"getting_started": "Test getting started"}),
    )

    # Act
    result = builder.algorithms

    # Assert
    assert isinstance(result, str)


def test_algorithms_empty_json(mock_markdown_builder_article):
    # Arrange
    builder = mock_markdown_builder_article(
        overview=json.dumps({"overview": "Test overview"}),
        content=json.dumps({"content": "Test content"}),
        algorithms=None,
        getting_started=json.dumps({"getting_started": "Test getting started"}),
    )

    # Act
    result = builder.algorithms

    # Assert
    assert result == ""


def test_toc_generation_article(mock_markdown_builder_article, llm_client, mock_model_handler):
    # Arrange
    builder = mock_markdown_builder_article(
        overview=json.dumps({"overview": "Test overview"}),
        content=json.dumps({"content": "Test content"}),
        algorithms=json.dumps({"algorithms": "Test algorithms"}),
        getting_started=json.dumps({"getting_started": "Test getting started"}),
    )
    llm_client.model_handler = mock_model_handler(side_effect=['{"citation": ""}'])

    with (
        patch("osa_tool.readmegen.models.llm_service.process_text") as mock_process,
        patch("osa_tool.readmegen.generator.base_builder.LLMClient", return_value=llm_client),
    ):
        mock_process.side_effect = lambda x: x

        # Act
        result = builder.toc

    # Assert
    assert isinstance(result, str)
    assert "- [" in result or "* [" in result
    assert "Citation" in result


def test_build_method_article_full(mock_markdown_builder_article, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = mock_markdown_builder_article(
        overview=json.dumps({"overview": "Test overview"}),
        content=json.dumps({"content": "Test content"}),
        algorithms=json.dumps({"algorithms": "Test algorithms"}),
        getting_started=json.dumps({"getting_started": "Test getting started"}),
    )
    builder.sourcerank = sourcerank

    with patch.object(MarkdownBuilderArticle, "_check_url", return_value=True):

        # Act
        result = builder.build()

    # Assert
    assert isinstance(result, str)
    assert len(result) > 0


def test_build_method_article_minimal(
    mock_markdown_builder_article,
    sourcerank_with_repo_tree,
    llm_client,
    mock_model_handler,
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = mock_markdown_builder_article(
        overview=json.dumps({"overview": ""}),
        content=json.dumps({"content": ""}),
        algorithms=json.dumps({"algorithms": ""}),
        getting_started=json.dumps({"getting_started": ""}),
    )
    builder.sourcerank = sourcerank

    llm_client.model_handler = mock_model_handler(side_effect=['{"citation": null}'])

    with (
        patch("osa_tool.readmegen.models.llm_service.process_text") as mock_process,
        patch("osa_tool.readmegen.generator.base_builder.LLMClient", return_value=llm_client),
        patch.object(MarkdownBuilderArticle, "_check_url", return_value=False),
    ):
        mock_process.side_effect = lambda x: x

        # Act
        result = builder.build()

    # Assert
    assert isinstance(result, str)
    assert "## Citation" in result
