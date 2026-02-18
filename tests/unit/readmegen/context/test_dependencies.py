from io import BytesIO
from unittest.mock import mock_open, patch

import pytest

from osa_tool.readmegen.context.dependencies import DependencyExtractor

# Sample tree used in all tests
MOCK_TREE = """
requirements.txt
pyproject.toml
setup.py
"""
BASE_PATH = "/fake/repo"


@pytest.fixture
def extractor():
    """
    Creates a DependencyExtractor instance using a mock tree and base path.
    
    Returns:
        DependencyExtractor: An instance of DependencyExtractor initialized with
        MOCK_TREE and BASE_PATH.
    """
    return DependencyExtractor(tree=MOCK_TREE, base_path=BASE_PATH)


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="requests==2.25.1\nnumpy>=1.20.0\n",
)
@patch(
    "osa_tool.readmegen.context.dependencies.find_in_repo_tree",
    return_value="requirements.txt",
)
def test_extract_from_requirements(mock_find, mock_file, extractor):
    """
    Test extraction of technologies from a requirements file.
    
    This test verifies that the extractor correctly parses a mocked
    requirements.txt file and returns a collection of technology names.
    The file is mocked to contain two dependencies: requests and numpy.
    The repository search is also mocked to return the path to the
    requirements file.
    
    Parameters
    ----------
    mock_find
        Mock object for the find_in_repo_tree function.
    mock_file
        Mock object for the builtins.open function.
    extractor
        Instance of the extractor under test.
    
    Returns
    -------
    None
    """
    # Act
    techs = extractor._extract_from_requirements()
    # Assert
    assert "requests" in techs
    assert "numpy" in techs


@patch(
    "osa_tool.readmegen.context.dependencies.find_in_repo_tree",
    return_value="pyproject.toml",
)
@patch(
    "builtins.open",
    new_callable=lambda: lambda f, mode="r", *args, **kwargs: BytesIO(
        b"""
[project]
dependencies = [
    "pandas >=1.0",
    "matplotlib"
]

[tool.poetry.dependencies]
python = ">=3.9"
scipy = "^1.8.0"
"""
    ),
)
def test_extract_from_pyproject(mock_file, mock_find, extractor):
    """
    Test extraction of dependencies from a pyproject.toml file.
    
    This test verifies that the extractor correctly parses the dependencies
    listed in a pyproject.toml file.  It uses mocked file contents and a mocked
    repository tree search to isolate the extraction logic.
    
    Parameters
    ----------
    mock_file : object
        Mocked file handler for the pyproject.toml content.
    mock_find : object
        Mocked function that simulates finding the pyproject.toml file in the repository.
    extractor : object
        Instance of the extractor under test.
    
    Returns
    -------
    None
        The function performs assertions and does not return a value.
    """
    # Act
    techs = extractor._extract_from_pyproject()
    # Assert
    assert "pandas" in techs
    assert "matplotlib" in techs
    assert "scipy" in techs


@patch(
    "builtins.open",
    new_callable=mock_open,
    read_data="""
from setuptools import setup

setup(
    name="my_package",
    install_requires=[
        "flask",
        "sqlalchemy >=1.4",
        "gunicorn"
    ],
    python_requires=">=3.7"
)
""",
)
@patch("osa_tool.readmegen.context.dependencies.find_in_repo_tree", return_value="setup.py")
def test_extract_from_setup(mock_find, mock_file, extractor):
    """
    Test that the extractor correctly parses dependencies from a setup.py file.
    
    Parameters
    ----------
    mock_find
        Mock object for the find_in_repo_tree function, returning the path to
        the setup.py file.
    mock_file
        Mock object for builtins.open, providing a fake setup.py content.
    extractor
        Instance of the extractor under test.
    
    Returns
    -------
    None
    """
    # Act
    techs = extractor._extract_from_setup()
    # Assert
    assert "flask" in techs
    assert "sqlalchemy" in techs
    assert "gunicorn" in techs


@patch(
    "osa_tool.readmegen.context.dependencies.DependencyExtractor._extract_from_requirements",
    return_value={"a"},
)
@patch(
    "osa_tool.readmegen.context.dependencies.DependencyExtractor._extract_from_pyproject",
    return_value={"b"},
)
@patch(
    "osa_tool.readmegen.context.dependencies.DependencyExtractor._extract_from_setup",
    return_value={"c"},
)
def test_extract_techs_combined(mock_setup, mock_pyproject, mock_req, extractor):
    """
    Test that DependencyExtractor.extract_techs combines technologies from setup, pyproject, and requirements.
    
    Parameters
    ----------
    mock_setup
        Mock for the _extract_from_setup method.
    mock_pyproject
        Mock for the _extract_from_pyproject method.
    mock_req
        Mock for the _extract_from_requirements method.
    extractor
        Instance of DependencyExtractor used to perform extraction.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the extracted technologies equal {"a", "b", "c"}.
    """
    # Act
    techs = extractor.extract_techs()
    # Assert
    assert techs == {"a", "b", "c"}
