import pytest


def test_git_auth_url_success(github_agent):
    """
    Test that the GitHub agent constructs the correct authenticated URL.
    
    Parameters
    ----------
    github_agent
        The GitHub agent instance used to generate the authentication URL.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the generated URL matches the expected value.
    """
    # Arrange
    expected_url = "https://test_token@github.com/testuser/testrepo.git"
    # Act
    auth_url = github_agent._get_auth_url()
    # Assert
    assert auth_url == expected_url


def test_get_auth_url_invalid_url_format(github_agent):
    """
    Test that `_get_auth_url` raises a `ValueError` when the repository URL is in an unsupported format.
    
    Args:
        github_agent: The GitHub agent instance whose `repo_url` is set to an
            unsupported SSH-style URL and whose `_get_auth_url` method is invoked
            to trigger the error.
    
    Returns:
        None
    """
    # Arrange
    github_agent.repo_url = "git@github.com:testuser/testrepo.git"
    # Assert
    with pytest.raises(ValueError, match="Unsupported repository URL format."):
        github_agent._get_auth_url()


@pytest.mark.parametrize(
    "method, exception_message",
    [
        ("create_fork", "Github token is required to create a fork."),
        ("star_repository", "Github token is required to star the repository."),
        ("create_pull_request", "Github token is required to create a pull request."),
        ("_get_auth_url", "Token not found in environment variables."),
    ],
)
def test_methods_require_token(method, exception_message, github_agent):
    """Test that all methods raise an exception when the GitHub token is missing."""
    # Arrange
    github_agent.token = None
    # Assert
    with pytest.raises(ValueError, match=exception_message):
        getattr(github_agent, method)()
