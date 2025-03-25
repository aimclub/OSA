import os
import pytest
from unittest import mock

from osa_tool.utils import (
    parse_folder_name,
    get_base_repo_url,
    delete_repository,
)


@pytest.fixture
def repo_url():
    return "https://github.com/username/repo-name"


@pytest.fixture
def expected_base_url():
    return "username/repo-name"


@pytest.fixture
def mock_os():
    with mock.patch("os.path.exists") as mock_exists, \
            mock.patch("shutil.rmtree") as mock_rmtree:
        yield mock_exists, mock_rmtree


def test_parse_folder_name_with_trailing_slash(repo_url):
    folder_name = parse_folder_name(repo_url + "/")
    assert folder_name == "repo-name"


def test_parse_folder_name_without_trailing_slash(repo_url):
    folder_name = parse_folder_name(repo_url)
    assert folder_name == "repo-name"


def test_get_base_repo_url_valid(repo_url, expected_base_url):
    result = get_base_repo_url(repo_url)
    assert result == expected_base_url


def test_get_base_repo_url_invalid(repo_url):
    with pytest.raises(ValueError, match="Unsupported repository URL format."):
        get_base_repo_url("inv" + repo_url)


def test_get_base_repo_url_with_trailing_slash(repo_url, expected_base_url):
    result = get_base_repo_url(repo_url + "/")
    assert result == expected_base_url


def test_delete_repository_existing(mock_os, repo_url):
    mock_exists, mock_rmtree = mock_os
    mock_exists.return_value = True

    delete_repository(repo_url)

    repo_path = os.path.join(os.getcwd(), "repo-name")
    mock_rmtree.assert_called_once_with(repo_path)


def test_delete_repository_non_existing(mock_os, repo_url):
    mock_exists, mock_rmtree = mock_os
    mock_exists.return_value = False

    delete_repository(repo_url)

    mock_rmtree.assert_not_called()


def test_delete_repository_failure(mock_os, repo_url):
    mock_exists, mock_rmtree = mock_os
    mock_exists.return_value = True
    mock_rmtree.side_effect = Exception("Deletion failed")

    with mock.patch("osa_tool.utils.logger") as mock_logger:
        delete_repository(repo_url)

    mock_logger.error.assert_called_with(
        "Failed to delete directory {}: Deletion failed".format(
            os.path.join(os.getcwd(), "repo-name")))
