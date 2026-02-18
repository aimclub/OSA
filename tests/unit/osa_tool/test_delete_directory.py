import os
from unittest.mock import patch

import pytest

from osa_tool.utils import delete_repository, parse_folder_name


@pytest.fixture
def mock_os():
    """
    Mock the `os.path.exists` and `shutil.rmtree` functions for testing.
    
    This context manager patches `os.path.exists` and `shutil.rmtree` using
    `unittest.mock.patch` and yields the corresponding mock objects.  Tests can
    inspect or configure these mocks to simulate file system behavior without
    affecting the real environment.
    
    Parameters
    ----------
    None
    
    Yields
    ------
    tuple
        A tuple containing two mock objects:
        1. `mock_exists` – the mock for `os.path.exists`.
        2. `mock_rmtree` – the mock for `shutil.rmtree`.
    
    Returns
    -------
    None
    """
    with patch("os.path.exists") as mock_exists, patch("shutil.rmtree") as mock_rmtree:
        yield mock_exists, mock_rmtree


def test_delete_repository_existing(mocker):
    """
    Test that delete_repository correctly deletes an existing repository.
    
    This test verifies that when a repository URL is provided, the
    `delete_repository` function constructs the expected local path,
    checks for its existence, and removes it using `shutil.rmtree`.  It
    patches `os.path.exists` to return `True` and ensures that the
    appropriate functions are called with the correct arguments.
    
    Parameters
    ----------
    mocker
        The pytest-mock fixture used to patch `os.path.exists` and
        `shutil.rmtree`.
    
    Returns
    -------
    None
        This test does not return a value.
    """
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
    """
    Test that `delete_repository` does not attempt to remove a repository when it does not exist.
    
    Parameters
    ----------
    mock_os : tuple
        Tuple containing mock objects for `os.path.exists` and `shutil.rmtree`. The first element
        is used to simulate the existence check, and the second element is used to verify that
        the removal function is not called.
    repo_url : str
        The URL or path of the repository to delete.
    
    Returns
    -------
    None
        This test function performs assertions on the mock objects and does not return a value.
    """
    # Arrange
    mock_exists, mock_rmtree = mock_os
    mock_exists.return_value = False
    # Act
    delete_repository(repo_url)
    # Assert
    mock_rmtree.assert_not_called()


def test_delete_repository_failure(mock_os, repo_url):
    """
    Test that `delete_repository` logs an error when directory deletion fails.
    
    Parameters
    ----------
    mock_os : tuple
        A tuple of mock objects used to replace `os.path.exists` and `os.rmtree`. The first element is configured to return ``True`` for existence checks, and the second element is set to raise an exception to simulate a deletion failure.
    repo_url : str
        The URL of the repository whose local directory is to be deleted.
    
    Returns
    -------
    None
    """
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
