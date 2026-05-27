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
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    raw_data = mock_api_raw_data
    original_languages = raw_data.get("languages", {})
    mock_response = mock_requests_response_factory(status_code=200, json_data=raw_data)
    languages_response = mock_requests_response_factory(status_code=200, json_data=original_languages)
    loader_class = LOADER_CLASSES[platform]

    # Act
    with patch("osa_tool.core.git.metadata.requests.get", side_effect=[mock_response, languages_response]) as mock_get:
        with patch.dict(os.environ, TOKEN_ENVS[platform]):
            result = loader_class._load_platform_data(repo_url, use_token=True)

    # Assert
    expected_payload = dict(raw_data)
    if isinstance(original_languages, dict):
        expected_payload["languages"] = list(original_languages.keys())
    else:
        expected_payload["languages"] = list(original_languages)
    if platform == "gitlab" and expected_payload["languages"] and not expected_payload.get("language"):
        expected_payload["language"] = expected_payload["languages"][0]
    if platform == "gitverse" and expected_payload["languages"] and not expected_payload.get("language"):
        expected_payload["language"] = expected_payload["languages"][0]
    expected = loader_class._parse_metadata(expected_payload)
    assert result == expected

    base_url = get_base_repo_url(repo_url)
    if platform == "gitlab":
        base_url = base_url.replace("/", "%2F")
        expected_url = BASE_URLS["gitlab"].format(base=base_url)
        expected_language_url = f"{expected_url}/languages"
    else:
        expected_url = BASE_URLS[platform].format(base=base_url)
        expected_language_url = raw_data["languages_url"]

    assert mock_get.call_count == 2
    first_call = mock_get.call_args_list[0]
    second_call = mock_get.call_args_list[1]
    assert first_call.kwargs == {"url": expected_url, "headers": HEADERS[platform]}
    assert second_call.kwargs == {"url": expected_language_url, "headers": HEADERS[platform]}


@pytest.mark.parametrize("mock_config_manager", ["github", "gitlab", "gitverse"], indirect=True)
@pytest.mark.parametrize("status_code", [401, 403, 404, 500])
def test_load_data_http_errors(status_code, mock_requests_response_factory, repo_info):
    # Arrange
    platform, _, _, repo_url = repo_info
    mock_response = mock_requests_response_factory(status_code=status_code)
    loader_class = LOADER_CLASSES[platform]

    # Act & Assert
    with patch("osa_tool.core.git.metadata.requests.get", return_value=mock_response):
        with patch.dict(os.environ, TOKEN_ENVS[platform]):
            with pytest.raises(Exception):
                loader_class.load_data(repo_url)
