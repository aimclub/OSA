import pytest


def test_git_auth_url_success(github_agent):
    # Arrange
    expected_url = "https://test_token@github.com/testuser/testrepo.git"
    # Act
    auth_url = github_agent._get_auth_url()
    # Assert
    assert auth_url == expected_url


def test_get_auth_url_invalid_url_format(github_agent):
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
