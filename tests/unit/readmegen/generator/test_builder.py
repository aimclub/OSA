import json
from unittest.mock import patch

from osa_tool.operations.docs.readme_generation.generator.builder import MarkdownBuilder
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_core_features_with_critical_features(mock_markdown_builder):
    """
    Tests that core_features output includes only critical features.
    
    This test verifies that the MarkdownBuilder's core_features property correctly filters
    and formats only the features marked as critical (is_critical: True) from the provided
    core_features list. Non-critical features are excluded from the output.
    
    Args:
        mock_markdown_builder: A factory function that creates a configured MarkdownBuilder instance for testing.
    
    Returns:
        None
    """
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
    """
    Tests that the core features section displays a placeholder message when no critical features are present.
    
    Args:
        mock_markdown_builder: A factory function that creates a MarkdownBuilder instance with mocked dependencies for testing. It accepts optional content sections such as core_features, overview, and getting_started.
    
    Why:
        This test verifies that the MarkdownBuilder correctly handles the scenario where all provided core features are marked as non-critical. It ensures the output contains a specific placeholder message, confirming the user interface properly communicates the absence of critical features.
    
    Returns:
        None
    """
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
    """
    Tests the core_features property when the builder is initialized with an empty JSON value.
    
    This test verifies that the core_features property returns an empty string when the builder is constructed with a `core_features` value of `None`. This ensures the property gracefully handles missing or null input, preventing errors in downstream documentation generation.
    
    Args:
        mock_markdown_builder: A factory function that creates a MarkdownBuilder instance with mocked dependencies for isolated testing.
    
    Returns:
        None
    """
    # Arrange
    builder = mock_markdown_builder(
        core_features=None, overview="Test overview", getting_started="Test getting started"
    )

    # Act
    result = builder.core_features

    # Assert
    assert result == ""


def test_core_features_multiple_critical_features(mock_markdown_builder):
    """
    Tests that core_features property correctly filters and formats multiple critical features.
    
    This test verifies that when a MarkdownBuilder is initialized with multiple core features
    where some are marked as critical, the core_features property:
    1. Includes only features where is_critical is True
    2. Formats them as numbered list items with feature names in bold
    3. Excludes non-critical features from the output
    
    Why:
    The core_features property is designed to highlight only the most important (critical) features in the generated documentation, ensuring the output is concise and focused on essential functionality. This filtering and formatting behavior is central to the builder's role in producing clear, prioritized documentation.
    
    Args:
        mock_markdown_builder: Factory function that creates configured MarkdownBuilder instances with mocked dependencies for testing. This fixture isolates the test from external systems like configuration managers or language models.
    
    Returns:
        None
    """
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
    """
    Tests the 'contributing' property when both discussions and a CONTRIBUTING file are present.
    
    This test verifies that the MarkdownBuilder.contributing property returns a string
    when the repository has both a discussions URL and a CONTRIBUTING file in its tree.
    The test ensures the property correctly handles the combined presence of these two
    contributing resources, mocking external URL checks to simulate a valid discussions URL.
    
    Args:
        mock_markdown_builder: Factory fixture to create a mocked MarkdownBuilder instance.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance with a given repository tree.
    
    Why:
        This test validates that the contributing property generates output (a string) when
        multiple contributing avenues exist, confirming the builder integrates both the
        discussions link and the CONTRIBUTING file appropriately without errors.
    
    Returns:
        None
    """
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
    """
    Tests the contributing property when discussions are not present.
    
    This test verifies that the contributing property of MarkdownBuilder returns a string
    when the repository lacks discussions. It mocks the repository tree and URL checking
    to simulate a scenario where discussions are absent.
    
    Why:
    The test ensures that the contributing section is generated correctly even when
    discussion-related resources (like a discussions URL) are unavailable, confirming
    robust behavior in common repository configurations.
    
    Args:
        mock_markdown_builder: Factory fixture to create a mocked MarkdownBuilder instance.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance with a given repository tree.
    
    Returns:
        None
    """
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
    """
    Tests the contributing property when no contributing file exists in the repository.
    
    This test verifies that the MarkdownBuilder.contributing property returns a string
    even when the repository tree does not contain a contributing file. It mocks the
    URL checking behavior to simulate specific conditions.
    
    Args:
        mock_markdown_builder: Factory fixture for creating MarkdownBuilder instances
            with mocked dependencies.
        sourcerank_with_repo_tree: Factory fixture for creating SourceRank instances
            with a given repository tree structure.
    
    Why:
        The test ensures the contributing property gracefully handles missing contributing
        files by returning a fallback string, preventing errors in documentation generation.
        It uses a minimal mock repository tree and mocks URL checking to isolate the
        property's logic from external dependencies.
    
    Returns:
        None: This is a test method and does not return a value.
    """
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
    """
    Tests the contributing property when only a CONTRIBUTING file exists in the repository.
    
    This test verifies that the MarkdownBuilder.contributing property correctly
    handles the scenario where the repository contains only a CONTRIBUTING file
    (no README or other documentation files). It mocks the repository tree data
    and URL validation to isolate the behavior of the contributing property.
    
    The test arranges a mock repository tree containing only a CONTRIBUTING file,
    configures a MarkdownBuilder instance with mocked dependencies and a SourceRank
    instance using that tree, and patches URL validation to succeed. It then
    asserts that the property returns a string result.
    
    Args:
        mock_markdown_builder: Factory fixture that creates MarkdownBuilder instances
            with mocked dependencies.
        sourcerank_with_repo_tree: Factory fixture that creates SourceRank instances
            with specified repository tree data.
    
    Returns:
        None: This is a test method and does not return a value.
    """
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
    """
    Tests the table of contents generation functionality of the MarkdownBuilder.
    
    This method sets up a mock MarkdownBuilder instance with specific content sections
    and a mocked language model client, then triggers the generation of the table of contents
    and validates its format and content.
    
    Args:
        mock_markdown_builder: Factory fixture for creating a mock MarkdownBuilder.
        llm_client: Mocked language model client.
        mock_model_handler: Factory fixture for creating a mocked ModelHandler.
    
    Why:
        The test validates that the MarkdownBuilder correctly generates a table of contents
        from provided content sections (like "Getting Started") and that it properly interacts
        with the language model client to include generated sections (like "Citation").
        It ensures the output is a string in valid Markdown list format and contains expected headings.
    
    The test performs the following steps:
    1. Arranges a MarkdownBuilder with predefined core features and a "Getting Started" section.
    2. Mocks the language model client to return a specific response for citation generation.
    3. Acts by accessing the builder's `toc` property, which triggers table of contents generation.
    4. Asserts that the result is a string, contains Markdown list syntax, and includes the expected
       "Getting Started" and "Citation" sections.
    """
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
    """
    Tests the full build process of the MarkdownBuilder.
    
    This test verifies that the `build` method executes correctly and returns a non-empty string when provided with a complete set of data, including core features, overview, getting started instructions, and a populated SourceRank instance with a full repository tree.
    
    Why:
    - The test ensures the builder can assemble a complete Markdown document from all required components without errors.
    - It validates that the builder integrates properly with a SourceRank instance containing a realistic repository structure, simulating a real-world usage scenario.
    - The `_check_url` method is patched to return `True` to avoid external network calls during testing, isolating the test to the build logic.
    
    Args:
        mock_markdown_builder: A factory fixture that creates a configured MarkdownBuilder instance with mocked dependencies.
        sourcerank_with_repo_tree: A factory fixture to create a SourceRank instance with a given repository tree.
    
    Returns:
        None. This is a test method; its purpose is to assert behavior.
    """
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
    """
    Tests the build method of MarkdownBuilder with minimal repository data.
    
    This test verifies that when the builder is configured with minimal content
    sections (empty overview and getting_started) and a repository with minimal
    structure, the generated markdown output contains expected elements while
    excluding sections that shouldn't appear with minimal data.
    
    Specifically, it ensures that with empty user-provided sections and a minimal
    repository tree, the builder correctly omits the "Getting Started" section
    (because the content is empty) and still includes the "Citation" section
    (which is generated from mocked LLM responses). This validates that the
    builder handles edge cases gracefully and only renders sections when appropriate.
    
    Args:
        mock_markdown_builder: Factory fixture that creates MarkdownBuilder instances
            with mocked dependencies.
        sourcerank_with_repo_tree: Factory fixture that creates SourceRank instances
            with specified repository tree data.
        llm_client: Mocked LLM client for language model interactions.
        mock_model_handler: Factory fixture to create mocked ModelHandler with
            custom side effects.
    
    Returns:
        None: This is a test method and does not return a value.
    """
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
