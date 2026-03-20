import os
from unittest.mock import patch

import pytest

from osa_tool.core.git.metadata import (
    GitHubMetadataLoader,
    GitLabMetadataLoader,
    GitverseMetadataLoader,
)
from osa_tool.utils.utils import get_base_repo_url

LOADER_CLASSES = {
    "github": GitHubMetadataLoader,
    "gitlab": GitLabMetadataLoader,
    "gitverse": GitverseMetadataLoader,
}

TOKEN_ENVS = {
    "github": {"GIT_TOKEN": "fake_token", "GITHUB_TOKEN": ""},
    "gitlab": {"GITLAB_TOKEN": "fake_token", "GIT_TOKEN": ""},
    "gitverse": {"GITVERSE_TOKEN": "fake_token", "GIT_TOKEN": ""},
}

BASE_URLS = {
    "github": "https://api.github.com/repos/{base}",
    "gitlab": "https://gitlab.com/api/v4/projects/{base}",
    "gitverse": "https://api.gitverse.ru/repos/{base}",
}

HEADERS = {
    "github": {
        "Authorization": "token fake_token",
        "Accept": "application/vnd.github.v3+json",
    },
    "gitlab": {
        "Authorization": "Bearer fake_token",
        "Content-Type": "application/json",
    },
    "gitverse": {
        "Authorization": "Bearer fake_token",
        "Accept": "application/vnd.gitverse.object+json;version=1",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    },
}


@pytest.mark.parametrize("mock_config_manager", ["github", "gitlab", "gitverse"], indirect=True)
def test_load_platform_data_success(mock_api_raw_data, mock_requests_response_factory, repo_info):
    """
    Tests successful loading of platform-specific repository metadata.
    
    This test verifies that the appropriate metadata loader class correctly
    fetches and parses repository data from the platform's API endpoint.
    It mocks the HTTP request and environment variables to simulate a
    successful API response, then compares the parsed result with expected
    metadata.
    
    The test is parameterized to run for multiple platforms (GitHub, GitLab, GitVerse)
    via the `mock_config_manager` fixture, ensuring each platform's loader behaves
    correctly under a successful API call.
    
    Args:
        mock_api_raw_data: Mock raw API response data for the repository.
        mock_requests_response_factory: Fixture providing a mock HTTP response factory.
        repo_info: Tuple containing platform name, repository owner, repository name,
            and repository URL.
    
    Why:
        This test ensures that each platform-specific metadata loader can successfully
        retrieve and parse repository data from its respective API. It validates the
        integration of the loader with the platform's API endpoint, including proper
        URL construction, header usage, and token handling, by mocking the external
        HTTP request to avoid network dependencies and focus on the loader's logic.
    """
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    raw_data = mock_api_raw_data
    mock_response = mock_requests_response_factory(status_code=200, json_data=raw_data)
    loader_class = LOADER_CLASSES[platform]

    # Act
    with patch("osa_tool.core.git.metadata.requests.get", return_value=mock_response) as mock_get:
        with patch.dict(os.environ, TOKEN_ENVS[platform]):
            result = loader_class._load_platform_data(repo_url, use_token=True)

    # Assert
    expected = loader_class._parse_metadata(raw_data)
    assert result == expected

    base_url = get_base_repo_url(repo_url)
    if platform == "gitlab":
        base_url = base_url.replace("/", "%2F")
        expected_url = BASE_URLS["gitlab"].format(base=base_url)
    else:
        expected_url = BASE_URLS[platform].format(base=base_url)

    mock_get.assert_called_once_with(
        url=expected_url,
        headers=HEADERS[platform],
    )


@pytest.mark.parametrize("mock_config_manager", ["github", "gitlab", "gitverse"], indirect=True)
@pytest.mark.parametrize("status_code", [401, 403, 404, 500])
def test_load_data_http_errors(status_code, mock_requests_response_factory, repo_info):
    """
    Tests that load_data raises an exception for specific HTTP error status codes.
    
    This test simulates HTTP error responses (e.g., 401, 403, 404, 500) from a
    remote repository platform and verifies that the platform-specific loader's
    `load_data` method raises an exception. The test is parameterized to run for
    multiple platforms (GitHub, GitLab, Gitverse) and each specified status code.
    
    Args:
        status_code: The HTTP status code to simulate in the mock response.
        mock_requests_response_factory: Fixture providing a factory to create mock
            HTTP responses.
        repo_info: A tuple containing platform identifier and repository URL
            information used to select the correct loader class.
    
    Why:
        This test ensures that the loader properly handles and propagates HTTP errors
        encountered during metadata retrieval. It validates that the loader does not
        silently ignore failures and that appropriate exceptions are raised for
        client and server errors, which is critical for robust error handling in the
        documentation pipeline.
    """
    # Arrange
    platform, _, _, repo_url = repo_info
    mock_response = mock_requests_response_factory(status_code=status_code)
    loader_class = LOADER_CLASSES[platform]

    # Act & Assert
    with patch("osa_tool.core.git.metadata.requests.get", return_value=mock_response):
        with patch.dict(os.environ, TOKEN_ENVS[platform]):
            with pytest.raises(Exception):
                loader_class.load_data(repo_url)
