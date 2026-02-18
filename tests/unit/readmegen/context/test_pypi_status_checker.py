from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.context.pypi_status_checker import PyPiPackageInspector


@pytest.fixture
def mock_setup_file_content():
    """
    Returns a string containing a minimal setup.py file for a test package.
    
    This function generates a template setup.py script that can be used in tests or
    mocking scenarios. The returned string includes a call to setuptools.setup
    with a name and version for a dummy package.
    
    Returns:
        str: A string representation of a simple setup.py file.
    """
    return """
    from setuptools import setup

    setup(
        name="test-package",
        version="0.1.0",
    )
    """


@pytest.fixture
def inspector():
    """
    Creates a PyPiPackageInspector instance with predefined mock configuration.
    
    This helper function constructs and returns a `PyPiPackageInspector` object
    configured with a mock tree and a mock base path. It is intended for use
    in testing or demonstration scenarios where a fully initialized inspector
    is required without relying on external resources.
    
    Returns:
        PyPiPackageInspector: An inspector initialized with the mock tree
        and mock base path.
    """
    return PyPiPackageInspector(tree="mock_tree", base_path="mock_base_path")


@patch("requests.get")
def test_get_package_version_from_pypi(mock_get, inspector):
    """
    Test that the inspector correctly retrieves a package's version from PyPI.
    
    This test verifies that the private method `_get_package_version_from_pypi` returns the
    expected version string when the `requests.get` call succeeds and returns a JSON
    payload containing the package information. A mocked `requests.get` is used to
    simulate a successful HTTP response with a status code of 200 and a JSON body
    containing the version.
    
    Args:
        mock_get: A mock object replacing `requests.get`, provided by the
            `@patch("requests.get")` decorator.
        inspector: An instance of the class containing the `_get_package_version_from_pypi`
            method, used to invoke the method under test.
    
    Returns:
        None
    """
    # Arrange
    mock_package_name = "test-package"
    mock_version = "1.0.0"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"info": {"version": mock_version}}
    mock_get.return_value = mock_response
    # Act
    version = inspector._get_package_version_from_pypi(mock_package_name)
    # Assert
    assert version == mock_version


@patch("requests.get")
def test_get_package_version_from_pypi_failure(mock_get, inspector):
    """
    Test that `_get_package_version_from_pypi` returns `None` when the package is not found on PyPI.
    
    Parameters
    ----------
    mock_get : MagicMock
        Mocked `requests.get` function patched by `@patch("requests.get")`.
    inspector : object
        Instance of the class under test that provides the `_get_package_version_from_pypi` method.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the method under test returns `None` when a 404 response is received.
    """
    # Arrange
    mock_package_name = "test-package"
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    # Act
    version = inspector._get_package_version_from_pypi(mock_package_name)
    # Assert
    assert version is None


@patch("requests.get")
def test_get_downloads_from_pepy(mock_get, inspector):
    """
    Test that the inspector's `_get_downloads_from_pepy` method correctly parses the
    download count from a Pepy API response.
    
    Parameters
    ----------
    mock_get : MagicMock
        Mocked `requests.get` function injected by the `@patch` decorator.
    inspector : object
        Instance of the class under test, providing the `_get_downloads_from_pepy`
        method.
    
    Returns
    -------
    None
    
    The test sets up a mock response with a status code of 200 and a JSON body
    containing a `total_downloads` field. It then calls
    `inspector._get_downloads_from_pepy` with a sample package name and asserts
    that the returned download count matches the mocked value.
    """
    # Arrange
    mock_package_name = "test-package"
    mock_downloads = 1000
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"total_downloads": mock_downloads}
    mock_get.return_value = mock_response
    # Act
    downloads = inspector._get_downloads_from_pepy(mock_package_name)
    # Assert
    assert downloads == mock_downloads


@patch("requests.get")
def test_get_downloads_from_pepy_failure(mock_get, inspector):
    """
    Test that `_get_downloads_from_pepy` returns `None` when the package is not found (HTTP 404).
    
    Parameters
    ----------
    mock_get : MagicMock
        Mocked `requests.get` function patched by `@patch("requests.get")`.
    inspector : object
        Instance of the class under test, providing the `_get_downloads_from_pepy` method.
    
    Returns
    -------
    None
        The test does not return a value; it asserts that the method under test returns `None` on a 404 response.
    """
    # Arrange
    mock_package_name = "test-package"
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    # Act
    downloads = inspector._get_downloads_from_pepy(mock_package_name)
    # Assert
    assert downloads is None


@patch("requests.get")
def test_is_published_on_pypi_success(mock_get, inspector):
    """
    Tests that the inspector correctly identifies a package as published on PyPI when the HTTP
    response status code is 200.
    
    Args:
        mock_get: The mocked `requests.get` function provided by the `@patch` decorator.
        inspector: An instance of the inspector class under test, which contains the
            `_is_published_on_pypi` method.
    
    Returns:
        None
    """
    # Arrange
    mock_package_name = "test-package"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    # Act
    is_published = inspector._is_published_on_pypi(mock_package_name)
    # Assert
    assert is_published is True


@patch("requests.get")
def test_is_published_on_pypi_failure(mock_get, inspector):
    """
    Test that the internal method `_is_published_on_pypi` correctly identifies a package
    as not published when the PyPI API returns a 404 status code.
    
    Args:
        mock_get: A mocked `requests.get` function provided by the `@patch` decorator.
        inspector: An instance of the class containing the `_is_published_on_pypi` method.
    
    Returns:
        None
    """
    # Arrange
    mock_package_name = "test-package"
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    # Act
    is_published = inspector._is_published_on_pypi(mock_package_name)
    # Assert
    assert is_published is False
