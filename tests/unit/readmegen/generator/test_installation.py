from unittest.mock import patch

from osa_tool.operations.docs.readme_generation.generator.installation import InstallationSectionBuilder
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_installation_builder_initialization(mock_installation_builder):
    """
    Verifies that the InstallationBuilder is correctly initialized with its required components.
    
    This test ensures that all essential attributes of the InstallationBuilder instance are properly set after initialization, confirming that the builder is ready for generating installation instructions.
    
    Args:
        mock_installation_builder: A mocked instance of the InstallationBuilder class used for testing.
    
    Attributes Verified:
        config_manager.config: The configuration settings loaded for the builder.
        repo_url: The URL of the repository being processed.
        _template: The template used for generating installation instructions.
        sourcerank: The SourceRank metadata associated with the repository.
    
    Why:
        The test validates that the builder's dependencies (configuration, repository URL, template, and metadata) are correctly injected and available, which is critical for the subsequent steps of documentation generation. Without these components, the builder would be unable to produce accurate installation instructions.
    """
    # Arrange
    builder = mock_installation_builder

    # Assert
    assert builder.config_manager.config is not None
    assert builder.repo_url is not None
    assert builder._template is not None
    assert builder.sourcerank is not None


def test_load_template(mock_installation_builder):
    """
    Verifies that the installation builder can successfully load a template as a dictionary.
    
    This test ensures that the `load_template` method returns a valid dictionary
    containing the expected structure, specifically checking for the presence of
    an "installation" key. It follows the Arrange-Act-Assert pattern for clarity.
    
    Args:
        mock_installation_builder: A mocked instance of the installation builder used for testing.
    
    Returns:
        None
    """
    # Arrange
    builder = mock_installation_builder

    # Act
    template = builder.load_template()

    # Assert
    assert isinstance(template, dict)
    assert "installation" in template


def test_python_requires_with_version(mock_installation_builder):
    """
    Verifies that the `_python_requires` method correctly formats and returns the Python version requirement string when a version is specified.
    
    This test ensures that the method produces a properly formatted string containing the Python version constraint, which is used to document or enforce Python version requirements in the installation configuration.
    
    Args:
        mock_installation_builder: A mock object representing the installation builder used to set up the test environment and version constraints.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_installation_builder
    builder.version = ">=3.8"

    # Act
    requirements = builder._python_requires()

    # Assert
    assert isinstance(requirements, str)
    assert "Python >=3.8" in requirements


def test_python_requires_without_version(mock_installation_builder):
    """
    Verifies that the `_python_requires` method returns an empty string when no Python version is specified in the installation builder.
    
    This test ensures that when the builder's version attribute is set to `None`, the method correctly returns an empty requirement string, indicating no Python version constraint.
    
    Args:
        mock_installation_builder: A mock object used to simulate an installation section builder.
    """
    # Arrange
    builder = mock_installation_builder
    builder.version = None

    # Act
    requirements = builder._python_requires()

    # Assert
    assert requirements == ""


def test_generate_install_command_with_pypi_info(mock_installation_builder):
    """
    Verifies that the installation command is correctly generated when PyPI information is available.
    
    This test ensures that the `_generate_install_command` method produces a valid pip install command string when the builder's info dictionary contains a package name. It checks both the type of the output and that the command includes the expected package name.
    
    Args:
        mock_installation_builder: A mocked instance of the installation section builder used to simulate package metadata. The test sets the builder's info to a dictionary with a "name" key to mimic PyPI metadata.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_installation_builder
    builder.info = {"name": "test-package"}

    # Act
    command = builder._generate_install_command()

    # Assert
    assert isinstance(command, str)
    assert "pip install test-package" in command


def test_generate_install_command_without_pypi_info(mock_installation_builder):
    """
    Verifies that the installation command generator correctly produces source-build instructions when PyPI information is unavailable.
    
    WHY: This test ensures that when no PyPI metadata is present, the system gracefully falls back to generic source-build instructions instead of failing or producing incorrect commands.
    
    Args:
        mock_installation_builder: A mocked instance of the installation section builder used for testing.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_installation_builder
    builder.info = None

    # Act
    command = builder._generate_install_command()

    # Assert
    assert isinstance(command, str)
    assert "Clone the" in command
    assert "Build from source" in command


def test_generate_install_command_with_requirements_txt(mock_installation_builder):
    """
    Verifies that the installation command generator correctly identifies and uses a requirements.txt file.
    
    This test mocks the repository tree search to simulate the presence of a requirements.txt file and asserts that the resulting installation command contains the appropriate pip install instruction. The test ensures the generator can locate a dependency file and format the correct pip command for installing from it.
    
    Args:
        mock_installation_builder: A mocked instance of the installation section builder used to invoke the command generation logic. Its `info` attribute is set to None for this test.
    
    Returns:
        None: This method performs assertions and does not return a value.
    """
    # Arrange
    builder = mock_installation_builder
    builder.info = None

    with patch(
        "osa_tool.operations.docs.readme_generation.generator.installation.find_in_repo_tree",
        return_value="requirements.txt",
    ):

        # Act
        command = builder._generate_install_command()

    # Assert
    assert isinstance(command, str)
    assert "pip install -r requirements.txt" in command


def test_build_installation(mock_installation_builder):
    """
    Verifies that the installation section is correctly built using the installation builder.
    
    This test ensures the builder produces a string output that contains the expected repository name,
    confirming proper integration of configuration data into the generated installation instructions.
    
    Args:
        mock_installation_builder: A mocked instance of the installation builder used to simulate the building process.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_installation_builder

    # Act
    installation = builder.build_installation()

    # Assert
    assert isinstance(installation, str)
    assert builder.config_manager.config.git.name in installation


def test_build_installation_with_python_version(mock_installation_builder):
    """
    Verifies that the installation section is correctly built when a specific Python version requirement is provided.
    This test ensures the builder properly incorporates Python version constraints into the generated installation instructions.
    
    Args:
        mock_installation_builder: A mocked builder object used to simulate the construction of installation instructions.
        The builder is configured with a version constraint (e.g., ">=3.8") and package info before building.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_installation_builder
    builder.version = ">=3.8"
    builder.info = {"name": "test-package"}

    # Act
    installation = builder.build_installation()

    # Assert
    assert isinstance(installation, str)
    assert "Python >=3.8" in installation
    assert "pip install test-package" in installation


def test_installation_builder_with_minimal_repo_tree(
    mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree
):
    """
    Tests the InstallationSectionBuilder with a minimal repository tree.
    
    This test verifies that the builder correctly initializes and constructs an installation section
    when provided with a minimal repository structure. It ensures the builder's dependencies are properly
    set and that the output is a formatted string.
    
    Args:
        mock_config_manager: Mock configuration manager.
        mock_repository_metadata: Mock repository metadata.
        sourcerank_with_repo_tree: Factory fixture that creates a SourceRank instance configured with a mock repository tree.
    
    Returns:
        None.
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = InstallationSectionBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Assert
    assert builder.config_manager.config is not None
    assert builder.sourcerank is not None

    installation = builder.build_installation()
    assert isinstance(installation, str)
