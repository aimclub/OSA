import os
from unittest.mock import patch

import pytest

from osa_tool.utils import delete_repository, parse_folder_name


@pytest.fixture
def mock_os():
    with patch("os.path.exists") as mock_exists, patch("shutil.rmtree") as mock_rmtree:
        yield mock_exists, mock_rmtree


def test_delete_repository_existing(mocker):
    # Arrange
    repo_url = "https://github.com/example/repo"
    expected_path = os.path.join(os.getcwd(), parse_folder_name(repo_url))
    mock_exists = mocker.patch("os.path.exists", return_value=True)
    mock_rmtree = mocker.patch("shutil.rmtree")
    # Act
    delete_repository(repo_url)
    # Assert
    mock_exists.assert_called_once_with(expected_path)
    mock_rmtree.assert_called_once_with(expected_path, onerror=mocker.ANY)


def test_delete_repository_non_existing(mock_os, repo_url):
    # Arrange
    mock_exists, mock_rmtree = mock_os
    mock_exists.return_value = False
    # Act
    delete_repository(repo_url)
    # Assert
    mock_rmtree.assert_not_called()


def test_delete_repository_failure(mock_os, repo_url):
    # Arrange
    mock_exists, mock_rmtree = mock_os
    mock_exists.return_value = True
    mock_rmtree.side_effect = Exception("Deletion failed")
    expected_folder_name = parse_folder_name(repo_url)
    expected_path = os.path.join(os.getcwd(), expected_folder_name)
    # Act
    with patch("osa_tool.utils.logger") as mock_logger:
        delete_repository(repo_url)
    # Assert
    mock_logger.error.assert_called_with(f"Failed to delete directory {expected_path}: Deletion failed")
