import pytest

from osa_tool.utils import parse_git_url


def test_parse_git_url_valid(repo_url):
    """
    Test that `parse_git_url` correctly parses a valid GitHub repository URL.
    
    Args:
        repo_url: The repository URL to parse.
    
    Returns:
        None
    
    This test calls `parse_git_url` with the provided `repo_url` and asserts that the
    returned components match the expected values for a GitHub URL:
    `host_domain` should be ``"github.com"``, `host` should be ``"github"``,
    `name` should be ``"repo-name"``, and `full_name` should be ``"username/repo-name"``.
    """
    # Act
    host_domain, host, name, full_name = parse_git_url(repo_url)
    # Assert
    assert host_domain == "github.com"
    assert host == "github"
    assert name == "repo-name"
    assert full_name == "username/repo-name"


@pytest.mark.parametrize(
    "invalid_url",
    [
        "ftp://github.com/user/repo",
        "git@github.com:user/repo.git",
        "://github.com/user/repo",
        "https:/github.com/user/repo",
    ],
)
def test_parse_git_url_invalid_scheme(invalid_url):
    """
    Test that `parse_git_url` raises a `ValueError` for URLs with unsupported or malformed schemes.
    
    Args:
        invalid_url: A string representing a git URL that is expected to be invalid due to
            an unsupported scheme or incorrect format.
    
    Returns:
        None
    
    Raises:
        ValueError: If `parse_git_url` does not raise a `ValueError` for the given `invalid_url`.
    
    Notes:
        This test is parameterized with several invalid URL examples, such as:
        - ``ftp://github.com/user/repo``
        - ``git@github.com:user/repo.git``
        - ``://github.com/user/repo``
        - ``https:/github.com/user/repo``
    
        The test verifies that each of these inputs correctly triggers a `ValueError` when
        passed to `parse_git_url`.
    """
    # Assert
    with pytest.raises(ValueError):
        parse_git_url(invalid_url)
