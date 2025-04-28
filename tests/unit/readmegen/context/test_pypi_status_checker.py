from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.context.pypi_status_checker import PyPiPackageInspector


@pytest.fixture
def mock_setup_file_content():
    return """
    from setuptools import setup

    setup(
        name="test-package",
        version="0.1.0",
    )
    """


@pytest.fixture
def inspector():
    return PyPiPackageInspector(tree="mock_tree", base_path="mock_base_path")


@patch('requests.get')
def test_get_package_version_from_pypi(mock_get, inspector):
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


@patch('requests.get')
def test_get_package_version_from_pypi_failure(mock_get, inspector):
    # Arrange
    mock_package_name = "test-package"
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    # Act
    version = inspector._get_package_version_from_pypi(mock_package_name)
    # Assert
    assert version is None


@patch('requests.get')
def test_get_downloads_from_pepy(mock_get, inspector):
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


@patch('requests.get')
def test_get_downloads_from_pepy_failure(mock_get, inspector):
    # Arrange
    mock_package_name = "test-package"
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    # Act
    downloads = inspector._get_downloads_from_pepy(mock_package_name)
    # Assert
    assert downloads is None


@patch('requests.get')
def test_is_published_on_pypi_success(mock_get, inspector):
    # Arrange
    mock_package_name = "test-package"
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_get.return_value = mock_response
    # Act
    is_published = inspector._is_published_on_pypi(mock_package_name)
    # Assert
    assert is_published is True


@patch('requests.get')
def test_is_published_on_pypi_failure(mock_get, inspector):
    # Arrange
    mock_package_name = "test-package"
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_get.return_value = mock_response
    # Act
    is_published = inspector._is_published_on_pypi(mock_package_name)
    # Assert
    assert is_published is False
