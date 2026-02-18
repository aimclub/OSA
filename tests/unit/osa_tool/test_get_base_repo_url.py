import pytest

from osa_tool.utils import get_base_repo_url


@pytest.fixture
def expected_base_url():
    """
    Return the expected base URL for the repository.
    
    This method returns a string representing the expected base URL
    for the repository in the format 'username/repo-name'.
    
    Returns:
        str: The expected base URL string.
    """
    return "username/repo-name"


def test_get_base_repo_url_valid(repo_url, expected_base_url):
    """
    Test that `get_base_repo_url` correctly extracts the base URL from a valid repository URL.
    
    Parameters
    ----------
    repo_url : str
        The full repository URL to be processed.
    expected_base_url : str
        The expected base URL that should be returned by `get_base_repo_url`.
    
    Returns
    -------
    None
    
    Raises
    ------
    AssertionError
        If the returned base URL does not match the expected value.
    """
    # Act
    result = get_base_repo_url(repo_url)
    # Assert
    assert result == expected_base_url


def test_get_base_repo_url_invalid(repo_url):
    """
    Tests that `get_base_repo_url` raises a `ValueError` when given an unsupported
    repository URL format.
    
    The function constructs an invalid URL by prefixing the supplied `repo_url`
    with the string ``"inv"`` and verifies that calling `get_base_repo_url` with
    this malformed URL triggers a `ValueError` with the expected error message.
    
    Args:
        repo_url: The original repository URL that will be prefixed with
            ``"inv"`` to create an invalid URL for testing.
    
    Returns:
        None
    """
    # Assert
    with pytest.raises(ValueError, match="Unsupported repository URL format."):
        get_base_repo_url("inv" + repo_url)


def test_get_base_repo_url_with_trailing_slash(repo_url, expected_base_url):
    """
    Test that `get_base_repo_url` correctly handles a repository URL with a trailing slash.
    
    Parameters
    ----------
    repo_url : str
        The repository URL to test, without a trailing slash.
    expected_base_url : str
        The expected base URL that should be returned by `get_base_repo_url`.
    
    Returns
    -------
    None
    """
    # Act
    result = get_base_repo_url(repo_url + "/")
    # Assert
    assert result == expected_base_url
