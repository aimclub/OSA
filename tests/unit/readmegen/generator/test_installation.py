from unittest.mock import patch

import pytest

from osa_tool.readmegen.generator.installation import InstallationSectionBuilder


def example_pypi_info():
    """
    Retrieves example PyPI package information.
    
    Returns:
        dict: A dictionary containing package metadata. The current implementation returns a
        dictionary with a single key ``name`` set to ``"cool-package"``.
    """
    return {"name": "cool-package"}


@pytest.fixture
def patch_dependencies():
    """
    Patch dependencies for testing and yield mock objects.
    
    This generator function temporarily patches several components used in the
    `osa_tool.readmegen.generator.installation` module.  It patches the data
    metadata loader, the source ranking class, the PyPI package inspector, and the
    dependency extractor.  After applying the patches, it yields the mock objects
    created for the rank, PyPI inspector, and dependency extractor so that test
    code can configure and inspect them.
    
    Parameters
    ----------
    None
    
    Yields
    ------
    tuple
        A tuple containing the mock objects in the following order:
        1. `mock_rank` – mock for `SourceRank`.
        2. `mock_pypi` – mock for `PyPiPackageInspector`.
        3. `mock_dep` – mock for `DependencyExtractor`.
    
    The generator automatically restores the original objects when it exits.
    """
    with (
        patch("osa_tool.readmegen.generator.installation.load_data_metadata"),
        patch("osa_tool.readmegen.generator.installation.SourceRank") as mock_rank,
        patch("osa_tool.readmegen.generator.installation.PyPiPackageInspector") as mock_pypi,
        patch("osa_tool.readmegen.generator.installation.DependencyExtractor") as mock_dep,
    ):

        yield mock_rank, mock_pypi, mock_dep


@pytest.fixture
def builder_with_pypi(config_loader, patch_dependencies):
    """
    Builds an InstallationSectionBuilder with mocked PyPI and dependency extraction for testing.
    
    Args:
        config_loader: The configuration loader used to construct the builder.
        patch_dependencies: A tuple containing mock objects for dependencies. The second
            element is a mock for the PyPI client, and the third element is a mock for
            the dependency extractor.
    
    Returns:
        An instance of InstallationSectionBuilder initialized with the provided
        configuration loader.
    """
    _, mock_pypi, mock_dep = patch_dependencies
    mock_pypi.return_value.get_info.return_value = example_pypi_info()
    mock_dep.return_value.extract_python_version_requirement.return_value = "3.11"

    return InstallationSectionBuilder(config_loader)


@pytest.fixture
def builder_from_source_with_reqs(config_loader, patch_dependencies):
    """
    Builds an InstallationSectionBuilder with mocked dependencies for testing.
    
    Parameters
    ----------
    config_loader
        The configuration loader to be passed to the builder.
    patch_dependencies
        A tuple of mock objects used to patch external dependencies. The tuple
        contains three mocks: mock_rank, mock_pypi, and mock_dep. These mocks
        are configured to simulate the presence of a requirements file,
        the absence of PyPI package information, and the absence of a Python
        version requirement extraction, respectively.
    
    Returns
    -------
    InstallationSectionBuilder
        An instance of InstallationSectionBuilder initialized with the provided
        config_loader, with the repository tree search patched to return
        "requirements.txt".
    """
    mock_rank, mock_pypi, mock_dep = patch_dependencies
    mock_rank.return_value.tree = "requirements.txt"
    mock_pypi.return_value.get_info.return_value = None
    mock_dep.return_value.extract_python_version_requirement.return_value = None

    with patch(
        "osa_tool.readmegen.generator.installation.find_in_repo_tree",
        return_value="requirements.txt",
    ):
        return InstallationSectionBuilder(config_loader)


@pytest.fixture
def builder_from_source_without_reqs(config_loader, patch_dependencies):
    """
    Builds an InstallationSectionBuilder instance with mocked dependencies for testing.
    
    Parameters
    ----------
    config_loader
        The configuration loader to be passed to the InstallationSectionBuilder.
    patch_dependencies
        A tuple containing mock objects for rank, pypi, and dependency extraction. The
        mocks are configured to return predetermined values: the rank mock's tree
        attribute is set to "mock_tree", the pypi mock's get_info method returns None,
        and the dependency mock's extract_python_version_requirement method returns
        "3.10".
    
    Returns
    -------
    InstallationSectionBuilder
        An instance of InstallationSectionBuilder initialized with the provided
        config_loader, with external dependencies patched to simulate a source
        without requirements.
    """
    mock_rank, mock_pypi, mock_dep = patch_dependencies
    mock_rank.return_value.tree = "mock_tree"
    mock_pypi.return_value.get_info.return_value = None
    mock_dep.return_value.extract_python_version_requirement.return_value = "3.10"

    with patch("osa_tool.readmegen.generator.installation.find_in_repo_tree", return_value=None):
        return InstallationSectionBuilder(config_loader)


def test_build_with_pypi(builder_with_pypi):
    """
    Test that the builder correctly generates a pip install command for a PyPI package and includes the required Python version.
    
    Parameters
    ----------
    builder_with_pypi
        A builder instance configured to build a PyPI package installation.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the generated installation string contains the expected pip command and Python version requirement.
    """
    # Act
    result = builder_with_pypi.build_installation()
    # Assert
    assert "pip install cool-package" in result
    assert "requires Python 3.11" in result


def test_build_from_source_with_requirements(builder_from_source_with_reqs):
    """
    Test building from source with requirements.
    
    This test verifies that the builder's `build_installation` method generates a
    command sequence that includes cloning the repository and installing dependencies
    from a `requirements.txt` file, and that it does not mention a generic Python
    requirement.
    
    Parameters
    ----------
    builder_from_source_with_reqs
        A fixture that provides a builder instance configured to build from source
        with a requirements file.
    
    Returns
    -------
    None
        The test does not return a value; it uses assertions to validate the
        expected output.
    """
    # Act
    result = builder_from_source_with_reqs.build_installation()
    # Assert
    assert "git clone" in result
    assert "pip install -r requirements.txt" in result
    assert "requires Python" not in result


def test_build_from_source_without_requirements(builder_from_source_without_reqs):
    """
    Test that building from source without requirements works correctly.
    
    Parameters
    ----------
    builder_from_source_without_reqs
        Fixture providing a builder configured to build from source without a requirements file.
    
    Returns
    -------
    None
    
    This test verifies that the build_installation method of the builder
    produces a command string that includes a git clone operation, does not
    include a pip install of a requirements.txt file, and contains a
    reference to requiring Python 3.10.
    """
    # Act
    result = builder_from_source_without_reqs.build_installation()
    # Assert
    assert "git clone" in result
    assert "pip install -r requirements.txt" not in result
    assert "requires Python 3.10" in result
