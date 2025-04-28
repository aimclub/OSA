import pytest

from osa_tool.utils import parse_git_url


def test_parse_git_url_valid(repo_url):
    # Act
    host_domain, host, name, full_name = parse_git_url(repo_url)
    # Assert
    assert host_domain == "github.com"
    assert host == "github"
    assert name == "repo-name"
    assert full_name == "username/repo-name"


@pytest.mark.parametrize("invalid_url", [
    "ftp://github.com/user/repo",
    "git@github.com:user/repo.git",
    "://github.com/user/repo",
    "https:/github.com/user/repo"
])
def test_parse_git_url_invalid_scheme(invalid_url):
    # Assert
    with pytest.raises(ValueError):
        parse_git_url(invalid_url)
