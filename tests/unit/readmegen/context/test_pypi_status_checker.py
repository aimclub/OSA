from unittest.mock import patch

import pytest

from osa_tool.operations.docs.readme_generation.context.pypi_status_checker import PyPiPackageInspector
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.mark.parametrize("tree_type", ["WITH_PYPROJECT", "WITH_SETUP", "MINIMAL"])
def test_get_published_package_name(tree_type, mock_requests_response_factory):
    # Arrange
    inspector = PyPiPackageInspector(get_mock_repo_tree(tree_type), base_path=".")

    with (
        patch("osa_tool.readme_generation.context.pypi_status_checker.read_file") as mock_read_file,
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
    content = """
[tool.poetry]
name = "mypoetry"
"""
    # Assert
    assert PyPiPackageInspector._extract_package_name_from_pyproject(content) == "mypoetry"


def test_extract_package_name_from_setup():
    # Arrange
    inspector = PyPiPackageInspector("", "")

    # Assert
    assert inspector._extract_package_name_from_setup('name="testpkg"') == "testpkg"
    assert inspector._extract_package_name_from_setup("no name here") is None


def test_get_info_success(mock_requests_response_factory):
    # Arrange
    inspector = PyPiPackageInspector(get_mock_repo_tree("WITH_PYPROJECT"), base_path=".")

    with (
        patch("osa_tool.readme_generation.context.pypi_status_checker.read_file") as mock_read_file,
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
    # Arrange
    inspector = PyPiPackageInspector(get_mock_repo_tree("MINIMAL"), base_path=".")
    # Assert
    assert inspector.get_info() is None


def test_get_package_version_from_pypi(mock_requests_response_factory):
    # Arrange
    inspector = PyPiPackageInspector("", "")

    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_requests_response_factory(200, json_data={"info": {"version": "9.9.9"}})

        # Act
        version = inspector._get_package_version_from_pypi("testpkg")

        # Assert
        assert version == "9.9.9"


def test_get_downloads_from_pepy(mock_requests_response_factory):
    # Arrange
    inspector = PyPiPackageInspector("", "")

    with patch("requests.get") as mock_get:
        mock_get.return_value = mock_requests_response_factory(200, json_data={"total_downloads": 888})

        # Act
        downloads = inspector._get_downloads_from_pepy("testpkg")

        # Assert
        assert downloads == 888
