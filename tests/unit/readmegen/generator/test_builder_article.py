import json
from unittest.mock import patch

from osa_tool.operations.docs.readme_generation.generator.builder_article import MarkdownBuilderArticle
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_content_section(mock_markdown_builder_article):
    """
    Tests the content property of a MarkdownBuilderArticle instance.
    
    This method verifies that the content property returns a string when the
    MarkdownBuilderArticle is constructed with a JSON string representing the
    content section. The test uses a factory function to create an isolated instance
    with mocked dependencies, ensuring the unit test focuses solely on the content
    property's behavior.
    
    Args:
        mock_markdown_builder_article: A factory function that creates a
            MarkdownBuilderArticle instance for testing. It accepts optional
            JSON string arguments for article sections (overview, content,
            algorithms, getting_started) and returns a builder initialized with
            those values and mocked dependencies.
    
    Returns:
        None
    """
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
    """
    Tests the content property when the content parameter is None, ensuring it returns an empty string.
    
    This test verifies that the MarkdownBuilderArticle's content property correctly handles a None input by returning an empty string, preventing null values in the generated documentation.
    
    Args:
        mock_markdown_builder_article: A factory function to create a MarkdownBuilderArticle instance for testing.
    
    Returns:
        None
    """
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
    """
    Tests the algorithms property of a MarkdownBuilderArticle instance.
    
    This method verifies that the algorithms property returns a string when the
    MarkdownBuilderArticle is constructed with a valid algorithms JSON component.
    The test ensures the property correctly extracts and returns the algorithms
    section content from the provided JSON data.
    
    Args:
        mock_markdown_builder_article: A factory function that creates a
            MarkdownBuilderArticle instance for testing. The factory accepts
            optional JSON string arguments for article components, including
            overview, content, algorithms, and getting_started.
    
    Returns:
        None
    """
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
    """
    Tests the algorithms property when the algorithms JSON is None.
    
    This test verifies that the property returns an empty string when the underlying algorithms data is None, ensuring proper handling of missing optional content.
    
    Args:
        mock_markdown_builder_article: A factory function to create MarkdownBuilderArticle test instances.
    
    Returns:
        None
    """
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
    """
    Tests the table of contents generation for an article builder.
    
    This test verifies that the `toc` property of a MarkdownBuilderArticle instance
    returns a valid table of contents string containing expected elements.
    The test mocks the LLM client and model handler to simulate a response without actual model inference, ensuring the test is isolated and repeatable.
    
    Args:
        mock_markdown_builder_article: Factory fixture to create a mocked MarkdownBuilderArticle. The fixture accepts optional article components (overview, content, algorithms, getting_started) to configure the builder instance.
        llm_client: Mocked LLM client used by the builder.
        mock_model_handler: Factory fixture to create a mocked ModelHandler. It is configured with a side effect to return a predefined JSON string for citation data.
    
    Returns:
        None
    """
    # Arrange
    builder = mock_markdown_builder_article(
        overview="Test overview",
        content="Test content",
        algorithms="Test algorithms",
        getting_started="Test getting started",
    )
    llm_client.model_handler = mock_model_handler(side_effect=['{"citation": ""}'])

    with patch("osa_tool.operations.docs.readme_generation.generator.base_builder.LLMClient", return_value=llm_client):
        # Act
        result = builder.toc

    # Assert
    assert isinstance(result, str)
    assert "- [" in result or "* [" in result
    assert "Citation" in result


def test_build_method_article_full(mock_markdown_builder_article, sourcerank_with_repo_tree):
    """
    Tests the build method of MarkdownBuilderArticle with a full repository tree.
    
    This test verifies that the builder correctly assembles a markdown article when provided with a complete mock repository structure. It ensures the output is a non‑empty string, confirming the build process works end‑to‑end under realistic conditions.
    
    Args:
        mock_markdown_builder_article: Factory fixture to create a MarkdownBuilderArticle instance for testing. The fixture accepts optional article components (overview, content, algorithms, getting_started) to configure the builder.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance with a given repository tree. The fixture injects a mock repository structure, isolating the test from actual filesystem or Git operations.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = mock_markdown_builder_article(
        overview="Test overview",
        content="Test content",
        algorithms="Test algorithms",
        getting_started="Test getting started",
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
    """
    Tests the build method of MarkdownBuilderArticle with minimal repository tree data.
    
    This test verifies that the builder correctly generates a markdown article string containing a citation section when provided with minimal repository structure data. It uses mocked dependencies to isolate the builder's behavior.
    
    Args:
        mock_markdown_builder_article: Factory fixture that creates MarkdownBuilderArticle instances.
        sourcerank_with_repo_tree: Factory fixture that creates SourceRank instances with repository tree data.
        llm_client: Mocked LLM client for language model interactions.
        mock_model_handler: Factory fixture to create mocked ModelHandler instances.
    
    The test performs the following steps:
    1. Arranges a minimal mock repository tree and configures a SourceRank instance with it.
    2. Creates a MarkdownBuilderArticle instance with empty article sections.
    3. Mocks the LLM client to return a JSON response with a null citation.
    4. Patches the URL validation to always return False, simulating an invalid or missing URL.
    5. Calls the builder's build method.
    6. Asserts the result is a string and contains a "## Citation" section.
    
    Why this is done: The test validates that the builder properly handles minimal input data and still generates a complete markdown structure, including the citation section, even when the LLM returns no citation data and URLs are invalid. This ensures robustness in edge-case scenarios.
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = mock_markdown_builder_article(
        overview="",
        content="",
        algorithms="",
        getting_started="",
    )
    builder.sourcerank = sourcerank

    llm_client.model_handler = mock_model_handler(side_effect=['{"citation": null}'])

    with (
        patch("osa_tool.operations.docs.readme_generation.generator.base_builder.LLMClient", return_value=llm_client),
        patch.object(MarkdownBuilderArticle, "_check_url", return_value=False),
    ):
        # Act
        result = builder.build()

    # Assert
    assert isinstance(result, str)
    assert "## Citation" in result
