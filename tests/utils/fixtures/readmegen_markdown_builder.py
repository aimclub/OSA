from unittest.mock import patch, MagicMock

import pytest

from osa_tool.operations.docs.readme_generation.generator.builder import MarkdownBuilder
from osa_tool.operations.docs.readme_generation.generator.builder_article import MarkdownBuilderArticle
from osa_tool.operations.docs.readme_generation.generator.header import HeaderBuilder
from osa_tool.operations.docs.readme_generation.generator.installation import InstallationSectionBuilder
from tests.utils.fixtures.analytics_sourcerank import sourcerank_with_repo_tree
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture
def mock_markdown_builder(mock_config_manager, mock_prompts, mock_repository_metadata):
    """
    Creates a factory function to instantiate MarkdownBuilder objects with mocked dependencies for testing.
    
    Args:
        mock_config_manager: The mocked configuration manager instance.
        mock_prompts: The mocked prompts or language model responses.
        mock_repository_metadata: The mocked metadata containing repository details.
    
    Returns:
        function: A closure that takes optional content sections (core_features, overview, getting_started) and returns a configured MarkdownBuilder instance. The returned builder is pre-configured with the provided mocks, and the content sections are passed directly to the MarkdownBuilder constructor if supplied.
    
    Why:
        This factory pattern is used to simplify the setup of MarkdownBuilder instances in unit tests by injecting mocked dependencies, isolating the builder from external systems like configuration files or language models.
    """
    def _create_builder(core_features=None, overview=None, getting_started=None):
        builder = MarkdownBuilder(
            config_manager=mock_config_manager,
            metadata=mock_repository_metadata,
            core_features=core_features,
            overview=overview,
            getting_started=getting_started,
        )
        return builder

    return _create_builder


@pytest.fixture
def mock_markdown_builder_article(mock_config_manager, mock_prompts, mock_repository_metadata):
    """
    Creates a factory function to instantiate MarkdownBuilderArticle objects for testing purposes.
    
    This mock factory is used to isolate tests from the actual construction and dependencies of MarkdownBuilderArticle, allowing controlled unit testing with predefined or mocked inputs.
    
    Args:
        mock_config_manager: The mocked configuration manager instance.
        mock_prompts: The mocked prompts or language model templates.
        mock_repository_metadata: The mocked metadata containing repository details.
    
    Returns:
        function: A factory function (_create_builder) that accepts optional article components and returns a MarkdownBuilderArticle instance. The factory function takes the following optional parameters:
            overview: Optional overview section content for the article.
            content: Optional main content for the article.
            algorithms: Optional algorithms section content.
            getting_started: Optional getting started guide content.
        The returned MarkdownBuilderArticle is initialized with the provided mocks and the given optional components.
    """
    def _create_builder(overview=None, content=None, algorithms=None, getting_started=None):
        builder = MarkdownBuilderArticle(
            config_manager=mock_config_manager,
            metadata=mock_repository_metadata,
            overview=overview,
            content=content,
            algorithms=algorithms,
            getting_started=getting_started,
        )
        return builder

    return _create_builder


@pytest.fixture
def mock_pypi_inspector():
    """
    Mocks the PyPiPackageInspector class for testing purposes.
    
    This method uses a context manager to patch the PyPiPackageInspector class within the readme generation module. It configures a mock instance to return a predefined dictionary containing package information (name, version, and downloads) when its get_info method is called. This allows tests to run without making actual network requests to PyPI, ensuring tests are fast, reliable, and isolated from external services.
    
    Args:
        None
    
    Yields:
        MagicMock: A mock object representing the PyPiPackageInspector class. When instantiated, it returns a configured mock instance whose get_info method returns a fixed dictionary with keys "name", "version", and "downloads".
    """
    with patch("osa_tool.operations.docs.readme_generation.generator.header.PyPiPackageInspector") as mock_inspector:
        mock_instance = MagicMock()
        mock_instance.get_info.return_value = {"name": "test-package", "version": "1.0.0", "downloads": 1000}
        mock_inspector.return_value = mock_instance
        yield mock_inspector


@pytest.fixture
def mock_dependency_extractor():
    """
    Creates a mock for the DependencyExtractor class to simulate technology extraction.
    
    This method uses a context manager to patch the DependencyExtractor in the
    osa_tool.operations.docs.readme_generation.generator.header module. It configures the mock instance
    to return a predefined set of technologies ("python", "numpy") when the
    extract_techs method is called.
    
    WHY: This mock is used in testing to isolate the dependency extraction logic,
    allowing tests to run without relying on the actual implementation of DependencyExtractor.
    
    Yields:
        MagicMock: A mock object representing the patched DependencyExtractor class.
        The mock is configured so that any instance created from it will have its
        extract_techs method return {"python", "numpy"}.
    """
    with patch("osa_tool.operations.docs.readme_generation.generator.header.DependencyExtractor") as mock_extractor:
        mock_instance = MagicMock()
        mock_instance.extract_techs.return_value = {"python", "numpy"}
        mock_extractor.return_value = mock_instance
        yield mock_extractor


@pytest.fixture
def mock_header_builder(
    mock_config_manager,
    mock_repository_metadata,
    mock_pypi_inspector,
    mock_dependency_extractor,
    sourcerank_with_repo_tree,
):
    """
    Constructs a mock HeaderBuilder instance for testing.
    
    This method creates a mock repository tree, uses it to generate a SourceRank
    instance, and initializes a HeaderBuilder with the provided mock configuration
    and metadata. The SourceRank's tree is then attached to the builder.
    This setup is useful for unit tests that require a controlled HeaderBuilder instance
    with a predefined repository structure, isolating tests from filesystem or Git operations.
    
    Args:
        mock_config_manager: Configuration manager mock.
        mock_repository_metadata: Repository metadata mock.
        mock_pypi_inspector: PyPI inspector mock (unused in this method).
        mock_dependency_extractor: Dependency extractor mock (unused in this method).
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance.
    
    Returns:
        HeaderBuilder: A HeaderBuilder instance configured with mock data and
        the tree from the generated SourceRank.
    """
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = HeaderBuilder(mock_config_manager, mock_repository_metadata)
    builder.tree = sourcerank.tree
    return builder


@pytest.fixture
def mock_installation_builder(
    mock_config_manager,
    mock_repository_metadata,
    mock_pypi_inspector,
    mock_dependency_extractor,
    sourcerank_with_repo_tree,
):
    """
    Creates a mock InstallationSectionBuilder instance with mocked dependencies and a SourceRank.
    
    This function is used in testing to construct an InstallationSectionBuilder with controlled, mocked dependencies and a SourceRank that is configured with a predefined mock repository tree. This setup isolates the builder from external systems (like filesystem or PyPI) and ensures consistent, repeatable test conditions.
    
    Args:
        mock_config_manager: Mock configuration manager.
        mock_repository_metadata: Mock repository metadata.
        mock_pypi_inspector: Mock PyPI inspector.
        mock_dependency_extractor: Mock dependency extractor.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance.
    
    Returns:
        InstallationSectionBuilder: A builder instance configured with the provided mocks and a SourceRank. The SourceRank is created using a full mock repository tree structure, and it is attached to the builder via the `sourcerank` attribute.
    """
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = InstallationSectionBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank
    return builder
