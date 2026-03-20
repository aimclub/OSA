from unittest.mock import patch

import pytest

from osa_tool.operations.docs.readme_generation.generator.base_builder import MarkdownBuilderBase
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture
def builder(mock_config_manager, mock_sourcerank, mock_repository_metadata):
    """
    Initializes and returns an instance of MarkdownBuilderBase configured with provided mock dependencies.
    
    Args:
        mock_config_manager: The configuration manager instance used for setting up the builder.
        mock_sourcerank: The SourceRank data provider used for repository scoring. This parameter is accepted but not used in the current implementation.
        mock_repository_metadata: The metadata provider containing information about the repository.
    
    Returns:
        MarkdownBuilderBase: A base markdown builder instance configured with the provided mocks.
    
    Note:
        The `mock_sourcerank` parameter is ignored in the current implementation; only `mock_config_manager` and `mock_repository_metadata` are passed to the MarkdownBuilderBase constructor.
    """
    return MarkdownBuilderBase(mock_config_manager, mock_repository_metadata)


def test_load_template_keys(builder):
    """
    Verifies that the loaded template contains the expected top-level keys.
    
    This test ensures the template structure is correct for downstream processing,
    which is critical for generating consistent documentation.
    
    Args:
        builder: The builder instance used to load the template.
    
    Asserts:
        Checks if 'overview', 'installation', 'license', and 'citation' keys are present in the loaded template.
    """
    # Act
    template = builder.load_template()

    # Assert
    assert "overview" in template
    assert "installation" in template
    assert "license" in template
    assert "citation" in template


def test_load_template_file_not_found(builder):
    """
    Verifies that the load_template method raises a FileNotFoundError when the specified template file does not exist.
    
    WHY: This test ensures that the builder correctly handles missing template files by raising the appropriate exception, validating error handling in the template loading process.
    
    Args:
        builder: The builder instance used to load the template.
    
    Raises:
        FileNotFoundError: If the template file is not found during the loading process.
    """
    with patch("osa_tool.operations.docs.readme_generation.generator.base_builder.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError):
            builder.load_template()


def test_overview_section(builder):
    """
    Verifies that the overview section of the builder is correctly formatted and contains the expected content.
    This test ensures the builder properly stores and returns the overview text with the required Markdown header formatting.
    
    Args:
        builder: The builder instance used to set and retrieve the overview content. The test directly sets the internal `_overview` attribute and then accesses the public `overview` property.
    
    Asserts:
        - The retrieved overview contains the assigned test string ("This is a test overview").
        - The result starts with the appropriate Markdown header for an overview section ("## Overview").
    """
    # Arrange
    builder._overview = "This is a test overview"

    # Act
    result = builder.overview

    # Assert
    assert "This is a test overview" in result
    assert result.startswith("## Overview")


def test_getting_started_section(builder):
    """
    Verifies that the getting started section is correctly formatted and contains the expected content.
    
    This is a unit test that ensures the builder correctly stores and retrieves the "Getting Started" section with proper Markdown formatting. It checks that the section includes the expected instructional content and begins with the appropriate heading.
    
    Args:
        builder: The builder instance used to set and retrieve the getting started section. The test sets a sample getting started instruction on this builder and then validates the returned value.
    
    Returns:
        None.
    """
    # Arrange
    builder._getting_started = "Run `make install`"

    # Act
    result = builder.getting_started

    # Assert
    assert "Run `make install`" in result
    assert result.startswith("## Getting Started")


def test_examples_section_with_examples(builder, sourcerank_with_repo_tree):
    """
    Tests the examples property of the builder when the repository tree contains example files.
    
    This test method configures a mock repository tree containing only examples,
    attaches it to the builder's sourcerank, and then verifies that the builder's
    examples property correctly identifies and formats the example files.
    
    Args:
        builder: The builder object whose examples property is under test.
        sourcerank_with_repo_tree: A fixture that creates a SourceRank instance
            configured with a specific repository tree. The fixture is called with
            a mock repository tree structure to inject into the builder's sourcerank.
    
    Returns:
        None
    
    Why:
        This test ensures that the builder correctly extracts and formats example
        files (such as Jupyter notebooks) from a repository tree, which is essential
        for generating accurate documentation sections. It validates that the
        examples property starts with the expected header and includes specific
        example file paths.
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("WITH_EXAMPLES_ONLY")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    # Act
    result = builder.examples

    # Assert
    assert "tutorials/getting_started.ipynb" in result
    assert result.startswith("## Examples")


def test_examples_section_no_examples(builder, sourcerank_with_repo_tree):
    """
    Tests that the examples property is an empty string when the repository tree is minimal.
    
    This test ensures that the builder's `examples` attribute correctly returns an empty string
    when the underlying repository contains no example files or directories. It uses a minimal
    mock repository tree to simulate a repository structure without any examples.
    
    Args:
        builder: The builder object under test, whose `examples` property is being validated.
        sourcerank_with_repo_tree: Factory fixture that creates a SourceRank instance configured
                                   with a specified mock repository tree.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    # Assert
    assert builder.examples == ""


def test_documentation_section_with_homepage(builder):
    """
    Verifies that the documentation section generated by the builder includes the homepage URL and follows the expected format.
    
    This test ensures the builder's documentation output correctly incorporates the project's homepage link and begins with the proper section header, validating both content inclusion and structural consistency.
    
    Args:
        builder: The builder instance used to generate documentation and metadata.
    
    Returns:
        None.
    """
    # Act
    result = builder.documentation

    # Assert
    assert builder.metadata.homepage_url in result
    assert result.startswith("## Documentation")


def test_documentation_section_with_local_docs(builder, sourcerank_with_repo_tree):
    """
    Tests the documentation section generation when local documentation files are present in the repository.
    
    This test verifies that the builder correctly constructs a documentation URL pointing to the local `/docs/` directory when the repository contains documentation files and no external homepage URL is set.
    
    Args:
        builder: The builder instance used to generate documentation.
        sourcerank_with_repo_tree: Factory fixture that creates a SourceRank instance configured with a specified mock repository tree.
    
    Returns:
        The generated documentation URL string, which is expected to include the path to the local `/docs/` directory.
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("WITH_DOCS")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.metadata.homepage_url = None

    # Act
    result = builder.documentation

    # Assert
    expected = builder.config_manager.config.git.repository + "/tree/" + builder.metadata.default_branch + "/docs/"
    assert expected in result


def test_documentation_section_empty(builder, sourcerank_with_repo_tree):
    """
    Tests that the documentation property returns an empty string when the repository tree is minimal and the homepage URL is not set.
    
    This test verifies the behavior of the documentation property under specific conditions: a minimal repository structure (no documentation files present) and no homepage URL provided. The property should return an empty string, indicating no documentation is available.
    
    Args:
        builder: The builder instance under test.
        sourcerank_with_repo_tree: Factory fixture that creates a SourceRank instance configured with a given mock repository tree.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.metadata.homepage_url = None

    # Assert
    assert builder.documentation == ""


def test_license_section_with_file(builder):
    """
    Verifies that the license section is correctly generated when a license name is provided.
    This test ensures the builder's license property includes both the license name and a standard "LICENSE" label, confirming proper formatting for documentation output.
    
    Args:
        builder: The builder instance used to generate metadata and license information.
    
    Returns:
        None.
    """
    # Arrange
    builder.metadata.license_name = "MIT"

    # Act
    result = builder.license

    # Assert
    assert "MIT" in result
    assert "LICENSE" in result


def test_license_section_empty(builder, sourcerank_with_repo_tree):
    """
    Tests that the license property returns an empty string when the license_name is None.
    
    This test ensures the builder's license property correctly handles the absence of a license
    by returning an empty string, which is the expected behavior for unlicensed repositories.
    
    Args:
        builder: The builder object under test.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance with a mock repository tree.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder.metadata.license_name = None

    # Assert
    assert builder.license == ""


def test_citation_section_with_file(builder, sourcerank_with_repo_tree):
    """
    Tests that the citation section is correctly generated when using a file-based repository tree.
    
    This test verifies that the builder's citation property produces the expected output when the underlying SourceRank instance is configured with a mock repository tree structure. This is important to ensure the citation generation logic works correctly in isolation from real filesystem or Git operations.
    
    Args:
        builder: The builder object used to generate the citation section.
        sourcerank_with_repo_tree: Factory fixture that creates a SourceRank instance configured with a specified repository tree.
    
    Returns:
        None
    """
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
    """
    Tests the citation section generation using an LLM client.
    
    This method verifies that the builder's citation property correctly
    generates a citation section containing the expected content from the LLM.
    It does this by mocking the repository tree and the LLM's response to isolate the test.
    
    Args:
        builder: The builder instance under test.
        sourcerank_with_repo_tree: Fixture that creates a SourceRank instance with a specified repository tree.
        llm_client: The LLM client used for generating citation text.
        mock_model_handler: Fixture that mocks the model handler to return a predefined response.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    llm_client.model_handler = mock_model_handler(side_effect=["LLM CITATION"])

    with patch("osa_tool.operations.docs.readme_generation.generator.base_builder.LLMClient", return_value=llm_client):
        # Act
        result = builder.citation

    # Assert
    assert "## Citation" in result
    assert "LLM CITATION" in result


def test_citation_section_fallback(builder, sourcerank_with_repo_tree, llm_client, mock_model_handler):
    """
    Tests the citation section fallback generation when the LLM returns empty content.
    
    This test verifies that when the LLM client returns an empty string for citation generation, the builder correctly falls back to a default citation template. The fallback ensures that required metadata elements (such as the repository owner and creation year) are still included in the citation section, maintaining essential attribution even when automated generation fails.
    
    Args:
        builder: The builder instance being tested.
        sourcerank_with_repo_tree: Factory fixture that creates a SourceRank instance configured with a mock repository tree.
        llm_client: The LLM client instance used for citation generation.
        mock_model_handler: Factory fixture that creates a mocked ModelHandler, configured here to return an empty string to simulate a failed LLM response.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    builder.sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    llm_client.model_handler = mock_model_handler(side_effect=[""])

    with patch("osa_tool.operations.docs.readme_generation.generator.base_builder.LLMClient", return_value=llm_client):
        # Act
        result = builder.citation

    # Assert
    assert "## Citation" in result
    assert builder.metadata.owner in result
    assert builder.metadata.created_at.split("-")[0] in result
