from unittest.mock import patch

from osa_tool.operations.docs.readme_generation.generator.installation import InstallationSectionBuilder
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_installation_builder_initialization(mock_installation_builder):
    # Arrange
    builder = mock_installation_builder

    # Assert
    assert builder.config is not None
    assert builder.repo_url is not None
    assert builder._template is not None
    assert builder.sourcerank is not None


def test_load_template(mock_installation_builder):
    # Arrange
    builder = mock_installation_builder

    # Act
    template = builder.load_template()

    # Assert
    assert isinstance(template, dict)
    assert "installation" in template


def test_python_requires_with_version(mock_installation_builder):
    # Arrange
    builder = mock_installation_builder
    builder.version = ">=3.8"

    # Act
    requirements = builder._python_requires()

    # Assert
    assert isinstance(requirements, str)
    assert "Python >=3.8" in requirements


def test_python_requires_without_version(mock_installation_builder):
    # Arrange
    builder = mock_installation_builder
    builder.version = None

    # Act
    requirements = builder._python_requires()

    # Assert
    assert requirements == ""


def test_generate_install_command_with_pypi_info(mock_installation_builder):
    # Arrange
    builder = mock_installation_builder
    builder.info = {"name": "test-package"}

    # Act
    command = builder._generate_install_command()

    # Assert
    assert isinstance(command, str)
    assert "pip install test-package" in command


def test_generate_install_command_without_pypi_info(mock_installation_builder):
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
    # Arrange
    builder = mock_installation_builder
    builder.info = None

    with patch("osa_tool.readme_generation.generator.installation.find_in_repo_tree", return_value="requirements.txt"):

        # Act
        command = builder._generate_install_command()

    # Assert
    assert isinstance(command, str)
    assert "pip install -r requirements.txt" in command


def test_build_installation(mock_installation_builder):
    # Arrange
    builder = mock_installation_builder

    # Act
    installation = builder.build_installation()

    # Assert
    assert isinstance(installation, str)
    assert builder.config.git.name in installation


def test_build_installation_with_python_version(mock_installation_builder):
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
    mock_config_loader, mock_repository_metadata, sourcerank_with_repo_tree
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = InstallationSectionBuilder(mock_config_loader, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Assert
    assert builder.config is not None
    assert builder.sourcerank is not None

    installation = builder.build_installation()
    assert isinstance(installation, str)
