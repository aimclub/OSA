import os
from unittest.mock import patch, ANY

import pytest

from osa_tool.core.git.metadata import (
    GitHubMetadataLoader,
    GitLabMetadataLoader,
    GitverseMetadataLoader,
    SourceCraftMetadataLoader,
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
    # Arrange
    platform, _, _, repo_url = repo_info
    mock_response = mock_requests_response_factory(status_code=status_code)
    loader_class = LOADER_CLASSES[platform]

    # Act & Assert
    with patch("osa_tool.core.git.metadata.requests.get", return_value=mock_response):
        with patch.dict(os.environ, TOKEN_ENVS[platform]):
            with pytest.raises(Exception):
                loader_class.load_data(repo_url)


# ---------------------------------------------------------------------------
# SourceCraft MetadataLoader — standalone tests (API format differs from other platforms)
# ---------------------------------------------------------------------------

_SC_REPO_URL = "https://sourcecraft.dev/testorg/testrepo"
_SC_API_URL = "https://api.sourcecraft.tech/repos/testorg/testrepo"
_SC_TOKEN_ENV = {"SOURCECRAFT_TOKEN": "fake_sc_token", "GIT_TOKEN": ""}


def _make_sc_raw_data() -> dict:
    return {
        "name": "testrepo",
        "slug": "testrepo",
        "description": "Test repository",
        "default_branch": "main",
        "last_updated": "2024-01-01T00:00:00Z",
        "visibility": "public",
        "web_url": "https://sourcecraft.dev/testorg/testrepo",
        "counters": {"forks": "3", "issues": "5"},
        "clone_url": {
            "https": "https://git@git.sourcecraft.dev/testorg/testrepo.git",
            "ssh": "git@git.sourcecraft.dev:testorg/testrepo.git",
        },
        "organization": {"slug": "testorg"},
        "language": {"name": "Python", "color": "#3572A5"},
    }


def test_sourcecraft_load_platform_data_success(mock_requests_response_factory):
    # Arrange
    raw_data = _make_sc_raw_data()
    mock_response = mock_requests_response_factory(status_code=200, json_data=raw_data)

    # Act
    with patch("osa_tool.core.git.metadata.requests.get", return_value=mock_response) as mock_get:
        with patch.dict(os.environ, _SC_TOKEN_ENV):
            result = SourceCraftMetadataLoader._load_platform_data(_SC_REPO_URL, use_token=True)

    # Assert
    expected = SourceCraftMetadataLoader._parse_metadata(raw_data)
    assert result == expected
    mock_get.assert_called_once_with(url=_SC_API_URL, headers=ANY)


@pytest.mark.parametrize("status_code", [401, 403, 404, 500])
def test_sourcecraft_load_data_http_errors(status_code, mock_requests_response_factory):
    # Arrange
    mock_response = mock_requests_response_factory(status_code=status_code)

    # Act & Assert
    with patch("osa_tool.core.git.metadata.requests.get", return_value=mock_response):
        with patch.dict(os.environ, _SC_TOKEN_ENV):
            with pytest.raises(Exception):
                SourceCraftMetadataLoader.load_data(_SC_REPO_URL)


def test_sourcecraft_parse_metadata_full_name():
    # full_name must be org_slug/repo_slug, not just repo_slug
    result = SourceCraftMetadataLoader._parse_metadata(_make_sc_raw_data())
    assert result.full_name == "testorg/testrepo"


def test_sourcecraft_parse_metadata_issues_url_includes_org():
    # issues_url must include both org and repo slugs
    result = SourceCraftMetadataLoader._parse_metadata(_make_sc_raw_data())
    assert result.issues_url == "https://sourcecraft.dev/testorg/testrepo/issues"


def test_sourcecraft_parse_metadata_counters_as_strings():
    # Counters arrive as strings from the API, should be parsed as ints
    raw = _make_sc_raw_data()
    raw["counters"] = {"forks": "7", "issues": "12"}
    result = SourceCraftMetadataLoader._parse_metadata(raw)
    assert result.forks_count == 7
    assert result.open_issues_count == 12


def test_sourcecraft_parse_metadata_language_none():
    # language=None must not raise and should yield empty string
    raw = _make_sc_raw_data()
    raw["language"] = None
    result = SourceCraftMetadataLoader._parse_metadata(raw)
    assert result.language == ""


def test_sourcecraft_parse_metadata_language_empty_dict():
    # language={} must not raise and should yield empty string
    raw = _make_sc_raw_data()
    raw["language"] = {}
    result = SourceCraftMetadataLoader._parse_metadata(raw)
    assert result.language == ""


def test_sourcecraft_parse_metadata_private_visibility():
    raw = _make_sc_raw_data()
    raw["visibility"] = "private"
    result = SourceCraftMetadataLoader._parse_metadata(raw)
    assert result.is_private is True


def test_sourcecraft_parse_metadata_public_visibility():
    raw = _make_sc_raw_data()
    raw["visibility"] = "public"
    result = SourceCraftMetadataLoader._parse_metadata(raw)
    assert result.is_private is False


def test_sourcecraft_parse_metadata_organization_none():
    # organization=null must not raise; owner/full_name/issues_url degrade gracefully
    raw = _make_sc_raw_data()
    raw["organization"] = None
    result = SourceCraftMetadataLoader._parse_metadata(raw)
    assert result.owner == ""
    assert result.owner_url is None
    assert result.issues_url == ""


def test_sourcecraft_parse_metadata_counters_none():
    # counters=null must not raise; counts default to 0
    raw = _make_sc_raw_data()
    raw["counters"] = None
    result = SourceCraftMetadataLoader._parse_metadata(raw)
    assert result.forks_count == 0
    assert result.open_issues_count == 0


def test_sourcecraft_parse_metadata_clone_url_none():
    # clone_url=null must not raise; URLs default to empty string
    raw = _make_sc_raw_data()
    raw["clone_url"] = None
    result = SourceCraftMetadataLoader._parse_metadata(raw)
    assert result.clone_url_http == ""
    assert result.clone_url_ssh == ""
