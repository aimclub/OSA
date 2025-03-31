import pytest

from osa_tool.utils import get_base_repo_url


@pytest.fixture
def expected_base_url():
    return "username/repo-name"


def test_get_base_repo_url_valid(repo_url, expected_base_url):
    # Act
    result = get_base_repo_url(repo_url)
    # Assert
    assert result == expected_base_url


def test_get_base_repo_url_invalid(repo_url):
    # Assert
    with pytest.raises(ValueError, match="Unsupported repository URL format."):
        get_base_repo_url("inv" + repo_url)


def test_get_base_repo_url_with_trailing_slash(repo_url, expected_base_url):
    # Act
    result = get_base_repo_url(repo_url + "/")
    # Assert
    assert result == expected_base_url
