import os
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.core.git.metadata import (
    GitHubMetadataLoader,
    GitLabMetadataLoader,
    GitverseMetadataLoader,
    LocalMetadataLoader,
    SourceCraftMetadataLoader,
)
from osa_tool.utils.utils import get_base_repo_url

LOADER_CLASSES = {
    "github": GitHubMetadataLoader,
    "gitlab": GitLabMetadataLoader,
    "gitverse": GitverseMetadataLoader,
    "sourcecraft": SourceCraftMetadataLoader,
}

TOKEN_ENVS = {
    "github": {"GIT_TOKEN": "fake_token", "GITHUB_TOKEN": ""},
    "gitlab": {"GITLAB_TOKEN": "fake_token", "GIT_TOKEN": ""},
    "gitverse": {"GITVERSE_TOKEN": "fake_token", "GIT_TOKEN": ""},
    "sourcecraft": {"SOURCECRAFT_TOKEN": "fake_token", "GIT_TOKEN": ""},
}

BASE_URLS = {
    "github": "https://api.github.com/repos/{base}",
    "gitlab": "https://gitlab.com/api/v4/projects/{base}",
    "gitverse": "https://api.gitverse.ru/repos/{base}",
    "sourcecraft": "https://api.sourcecraft.tech/repos/{base}",
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
    "sourcecraft": {
        "Authorization": "Bearer fake_token",
        "Accept": "application/json",
        "Content-Type": "application/json",
    },
}


@pytest.mark.parametrize("mock_config_manager", ["github", "gitlab", "gitverse", "sourcecraft"], indirect=True)
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

    if platform == "gitlab":
        base_url = get_base_repo_url(repo_url).replace("/", "%2F")
        expected_url = BASE_URLS["gitlab"].format(base=base_url)
    elif platform == "sourcecraft":
        expected_url = BASE_URLS["sourcecraft"].format(base=f"{owner}/{repo_name}")
    else:
        expected_url = BASE_URLS[platform].format(base=get_base_repo_url(repo_url))

    mock_get.assert_called_once_with(
        url=expected_url,
        headers=HEADERS[platform],
    )


@pytest.mark.parametrize("mock_config_manager", ["github", "gitlab", "gitverse", "sourcecraft"], indirect=True)
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


# Sourcecraft


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


def test_github_parse_metadata_strips_issue_template_suffix():
    raw = {
        "name": "repo",
        "full_name": "owner/repo",
        "owner": {"login": "owner", "html_url": "https://github.com/owner"},
        "description": "desc",
        "stargazers_count": 1,
        "forks_count": 2,
        "watchers_count": 3,
        "open_issues_count": 4,
        "default_branch": "main",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "pushed_at": "2024-01-03T00:00:00Z",
        "size": 10,
        "clone_url": "https://github.com/owner/repo.git",
        "ssh_url": "git@github.com:owner/repo.git",
        "contributors_url": "https://api.github.com/repos/owner/repo/contributors",
        "languages_url": "https://api.github.com/repos/owner/repo/languages",
        "issues_url": "https://api.github.com/repos/owner/repo/issues{/number}",
        "language": "Python",
        "languages": {},
        "topics": [],
        "has_wiki": False,
        "has_issues": True,
        "has_projects": False,
        "private": False,
        "homepage": "",
        "license": {},
    }

    result = GitHubMetadataLoader._parse_metadata(raw)

    assert result.issues_url == "https://api.github.com/repos/owner/repo/issues"


def test_gitverse_parse_metadata_strips_issue_template_suffix():
    raw = {
        "name": "repo",
        "full_name": "owner/repo",
        "owner": {"login": "owner", "html_url": "https://gitverse.ru/owner"},
        "description": "desc",
        "stargazers_count": 1,
        "forks_count": 2,
        "watchers_count": 3,
        "open_issues_count": 4,
        "default_branch": "main",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "pushed_at": "2024-01-03T00:00:00Z",
        "size": 10,
        "clone_url": "https://gitverse.ru/owner/repo.git",
        "ssh_url": "git@gitverse.ru:owner/repo.git",
        "contributors_url": "https://api.gitverse.ru/repos/owner/repo/contributors",
        "languages_url": "https://api.gitverse.ru/repos/owner/repo/languages",
        "issues_url": "https://api.gitverse.ru/repos/owner/repo/issues{/number}",
        "language": "Python",
        "languages": [],
        "topics": [],
        "has_wiki": False,
        "has_issues": True,
        "has_projects": False,
        "private": False,
        "homepage": "",
        "license": {},
    }

    result = GitverseMetadataLoader._parse_metadata(raw)

    assert result.issues_url == "https://api.gitverse.ru/repos/owner/repo/issues"


def test_local_metadata_loader_falls_back_when_git_user_config_missing(tmp_path):
    repo_path = tmp_path / "local_repo"
    repo_path.mkdir()

    mock_repo = MagicMock()
    mock_reader = MagicMock()
    mock_reader.get.side_effect = Exception("missing config")
    mock_repo.config_reader.return_value = mock_reader

    with patch("osa_tool.core.git.metadata.Repo", return_value=mock_repo):
        with patch.object(LocalMetadataLoader, "_load_dates", return_value={"created_at": "", "updated_at": "", "pushed_at": ""}):
            with patch.object(LocalMetadataLoader, "_get_repository_size", return_value=0):
                with patch.object(LocalMetadataLoader, "_get_languages", return_value=[]):
                    with patch.object(LocalMetadataLoader, "_get_remotes", return_value={"clone_url_http": "", "clone_url_ssh": ""}):
                        with patch.object(LocalMetadataLoader, "_get_default_branch", return_value="main"):
                            with patch.object(LocalMetadataLoader, "_find_license", return_value=None):
                                result = LocalMetadataLoader._load_platform_data(str(repo_path), use_token=False)

    assert result.owner is None
    assert result.owner_url is None
