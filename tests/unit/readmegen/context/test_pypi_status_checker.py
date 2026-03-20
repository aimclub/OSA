from unittest.mock import patch

import pytest

from osa_tool.operations.docs.readme_generation.context.pypi_status_checker import PyPiPackageInspector
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.mark.parametrize("tree_type", ["WITH_PYPROJECT", "WITH_SETUP", "MINIMAL"])
def test_get_published_package_name(tree_type, mock_requests_response_factory):
    """
    Tests the get_published_package_name method of PyPiPackageInspector for different repository tree configurations.
    
    This test method uses mocking to simulate different project file structures (pyproject.toml, setup.py, or neither) and HTTP responses to verify the behavior of the package name detection and PyPI publication check. The test ensures the method correctly extracts the package name from available project files and checks its publication status on PyPI, returning None when no project file exists.
    
    Args:
        tree_type: Specifies the type of mock repository tree to test. Determines which project file is present. Valid values are "WITH_PYPROJECT", "WITH_SETUP", and "MINIMAL".
        mock_requests_response_factory: A fixture providing a factory to create mock HTTP responses for requests.get.
    
    Returns:
        None: This is a test method and does not return a value.
    """
    # Arrange
    inspector = PyPiPackageInspector(get_mock_repo_tree(tree_type), base_path=".")

    with (
        patch("osa_tool.operations.docs.readme_generation.context.pypi_status_checker.read_file") as mock_read_file,
        patch("requests.get") as mock_get,
    ):

        # Assert
        if tree_type == "WITH_PYPROJECT":
            mock_read_file.return_value = """
[project]
name = "mockproject"
"""
            mock_get.return_value = mock_requests_response_factory(200)
            assert inspector.get_published_package_name() == "mockproject"

        elif tree_type == "WITH_SETUP":
            mock_read_file.return_value = 'name="mocksetup"'
            mock_get.return_value = mock_requests_response_factory(200)
            assert inspector.get_published_package_name() == "mocksetup"

        else:  # MINIMAL — ни setup.py, ни pyproject.toml
            assert inspector.get_published_package_name() is None


def test_extract_package_name_from_pyproject():
    """
    Verifies that the `_extract_package_name_from_pyproject` method correctly parses and returns the package name from a string representing a pyproject.toml file.
    
    This test ensures the method accurately extracts the package name from a pyproject.toml content string, which is essential for identifying Poetry-based packages in repository analysis. It validates the parsing logic against a simple, valid TOML example.
    
    Args:
        content: A string containing pyproject.toml content with a [tool.poetry] section and a name field.
    
    Returns:
        None. The test passes if the extracted name matches the expected value; otherwise, it raises an assertion error.
    """
    content = """
[tool.poetry]
name = "mypoetry"
"""
    # Assert
    assert PyPiPackageInspector._extract_package_name_from_pyproject(content) == "mypoetry"


def test_extract_package_name_from_setup():
    """
    Verifies that the _extract_package_name_from_setup method correctly parses package names from setup script strings.
    
    This test case checks the extraction logic for valid name assignments and ensures it returns None when no name is found.
    The test is necessary to validate the helper method's ability to parse setup.py-like strings, which is critical for accurately identifying package names during repository inspection.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    inspector = PyPiPackageInspector("", "")

    # Assert
    assert inspector._extract_package_name_from_setup('name="testpkg"') == "testpkg"
    assert inspector._extract_package_name_from_setup("no name here") is None


def test_get_info_success(mock_requests_response_factory):
    """
    Verifies that the `get_info` method successfully retrieves and aggregates package information from pyproject.toml and external APIs.
    
    This test mocks file reading to simulate a pyproject.toml file and patches network requests to simulate responses from PyPI and PePy. It validates that the `PyPiPackageInspector` correctly parses the project name and combines it with version and download data fetched from the respective services.
    
    Args:
        mock_requests_response_factory: A factory fixture used to create mock HTTP response objects with specific status codes and JSON data.
    
    Why:
    - The test isolates external dependencies (file I/O and network calls) to ensure reliable, fast unit testing.
    - It confirms that the inspector integrates data from multiple sources (local pyproject.toml, PyPI for version, PePy for downloads) into a single dictionary.
    - The mocked responses simulate successful API calls (HTTP 200) to verify the normal, error‑free flow of `get_info`.
    """
    # Arrange
    inspector = PyPiPackageInspector(get_mock_repo_tree("WITH_PYPROJECT"), base_path=".")

    with (
        patch("osa_tool.operations.docs.readme_generation.context.pypi_status_checker.read_file") as mock_read_file,
        patch("requests.get") as mock_get,
    ):

        mock_read_file.return_value = """
[project]
name = "mockproject"
"""

        def side_effect(url, *args, **kwargs):
            if "pypi.org" in url:
                return mock_requests_response_factory(200, json_data={"info": {"version": "1.2.3"}})
            elif "pepy.tech" in url:
                return mock_requests_response_factory(200, json_data={"total_downloads": 12345})
            return mock_requests_response_factory(404)

        mock_get.side_effect = side_effect

        # Act
        result = inspector.get_info()

        # Assert
        assert result == {"name": "mockproject", "version": "1.2.3", "downloads": 12345}


def test_get_info_not_published():
    """
    Verifies that the get_info method returns None when the package is not published.
    
    This test case initializes a PyPiPackageInspector with a minimal repository tree and asserts that the metadata retrieval fails gracefully by returning None.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    inspector = PyPiPackageInspector(get_mock_repo_tree("MINIMAL"), base_path=".")
    # Assert
    assert inspector.get_info() is None


def test_get_package_version_from_pypi(mock_requests_response_factory):
    """
    Verifies that the `_get_package_version_from_pypi` method correctly retrieves and returns the package version from the PyPI API. This test uses mocking to isolate the HTTP request and confirm the method parses the expected version from the PyPI JSON response.
    
    Args:
        mock_requests_response_factory: A factory fixture used to create mock HTTP response objects for simulating PyPI API responses.
    
    Returns:
        None.
    """
    # Arrange
    inspector = PyPiPackageInspector("", "")

    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_requests_response_factory(200, json_data={"info": {"version": "9.9.9"}})

        # Act
        version = inspector._get_package_version_from_pypi("testpkg")

        # Assert
        assert version == "9.9.9"


def test_get_downloads_from_pepy(mock_requests_response_factory):
    """
    Verifies that the `_get_downloads_from_pepy` method correctly retrieves and parses the total download count from the PePy API.
    
    This test ensures the method handles the API response properly and extracts the expected download count from the JSON data.
    
    Args:
        mock_requests_response_factory: A factory fixture used to create mock HTTP response objects. It is configured to simulate a successful PePy API response containing a `total_downloads` field.
    
    Returns:
        None.
    """
    # Arrange
    inspector = PyPiPackageInspector("", "")

    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_requests_response_factory(200, json_data={"total_downloads": 888})

        # Act
        downloads = inspector._get_downloads_from_pepy("testpkg")

        # Assert
        assert downloads == 888
