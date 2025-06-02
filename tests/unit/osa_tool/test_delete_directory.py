import os
import pytest
from unittest.mock import patch

from osa_tool.utils import delete_repository


@pytest.fixture
def mock_os():
    with patch("os.path.exists") as mock_exists, patch("shutil.rmtree") as mock_rmtree:
        yield mock_exists, mock_rmtree


def test_delete_repository_existing(mock_os, repo_url):
    # Arrange
    mock_exists, mock_rmtree = mock_os
    mock_exists.return_value = True
    # Act
    delete_repository(repo_url)
    # Assert
    repo_path = os.path.join(os.getcwd(), "repo-name")
    mock_rmtree.assert_called_once_with(repo_path)


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
    # Act
    with patch("osa_tool.utils.logger") as mock_logger:
        delete_repository(repo_url)
    # Assert
    mock_logger.error.assert_called_with(
        "Failed to delete directory {}: Deletion failed".format(
            os.path.join(os.getcwd(), "repo-name")
        )
    )
