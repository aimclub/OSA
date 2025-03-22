import pytest

from osa_tool.utils import (
    parse_folder_name,
)


@pytest.fixture
def repo_url():
    return "https://github.com/user/repo-name"


def test_parse_folder_name(repo_url):
    # Test valid URL
    folder_name = parse_folder_name(repo_url + "/")
    assert folder_name == "repo-name"

    # Test URL without trailing slash
    folder_name = parse_folder_name(repo_url)
    assert folder_name == "repo-name"
