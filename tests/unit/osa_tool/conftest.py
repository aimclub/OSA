import pytest


@pytest.fixture
def repo_url():
    """
    Return the URL of the repository.
    
    Returns:
        str: The GitHub repository URL.
    """
    return "https://github.com/username/repo-name"
