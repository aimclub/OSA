from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from osa_tool.utils.utils import (
    detect_provider_from_url,
    extract_readme_content,
    get_base_repo_url,
    osa_project_root,
    parse_folder_name,
    parse_git_url,
)


def test_parse_folder_name_github():
    # Arrange
    repo_url = "https://github.com/user/repo-name"

    # Act
    folder_name = parse_folder_name(repo_url)

    # Assert
    assert folder_name == "repo-name"


def test_parse_folder_name_gitlab():
    # Arrange
    repo_url = "https://gitlab.com/user/repo-name"

    # Act
    folder_name = parse_folder_name(repo_url)

    # Assert
    assert folder_name == "repo-name"


def test_parse_folder_name_gitverse():
    # Arrange
    repo_url = "https://gitverse.ru/user/repo-name"

    # Act
    folder_name = parse_folder_name(repo_url)

    # Assert
    assert folder_name == "repo-name"


def test_osa_project_root():
    # Act
    root = osa_project_root()

    # Assert
    assert isinstance(root, Path)
    assert root.name == "osa_tool" or root.exists()


def test_get_base_repo_url_github():
    # Arrange
    repo_url = "https://github.com/user/repo-name"

    # Act
    base_url = get_base_repo_url(repo_url)

    # Assert
    assert base_url == "user/repo-name"


def test_get_base_repo_url_gitlab():
    # Arrange
    repo_url = "https://gitlab.com/group/subgroup/repo-name"

    # Act
    base_url = get_base_repo_url(repo_url)

    # Assert
    assert base_url == "group/subgroup/repo-name"


def test_get_base_repo_url_gitverse():
    # Arrange
    repo_url = "https://gitverse.ru/user/repo-name"

    # Act
    base_url = get_base_repo_url(repo_url)

    # Assert
    assert base_url == "user/repo-name"


def test_get_base_repo_url_invalid():
    # Arrange
    repo_url = "https://invalid.com/repo"

    # Act
    with pytest.raises(ValueError):
        get_base_repo_url(repo_url)


def test_parse_git_url_https():
    # Arrange
    repo_url = "https://github.com/user/repo-name"

    # Act
    host_domain, host, name, full_name = parse_git_url(repo_url)

    # Assert
    assert host_domain == "github.com"
    assert host == "github"
    assert name == "repo-name"
    assert full_name == "user/repo-name"


def test_parse_git_url_invalid_scheme():
    # Arrange
    repo_url = "ftp://github.com/user/repo-name"

    # Act
    with pytest.raises(ValueError):
        parse_git_url(repo_url)


def test_parse_git_url_invalid_url():
    # Arrange
    repo_url = "not-a-url"

    # Assert
    with pytest.raises(ValueError):
        parse_git_url(repo_url)


@pytest.mark.parametrize(
    "base_url,api",
    [
        ("https://api.openai.com/v1/chat/completions", "openai"),
        ("https://openrouter.ai/api/v1", "openai"),
        ("https://api.vsegpt.ru/v1", "openai"),
        ("https://gigachat.devices.sberbank.ru/api/v1", "openai"),
    ],
)
def test_detect_model_openai_provider(base_url, api):
    assert detect_provider_from_url(base_url) == api


@pytest.mark.parametrize(
    "base_url,api",
    [
        ("http://10.9.0.1:11434/api/generate", "ollama"),
        ("http://localhost:11434/api/generate", "ollama"),
    ],
)
def test_detect_model_ollama_provider(base_url, api):
    assert detect_provider_from_url(base_url) == api


@pytest.mark.parametrize(
    "base_url,api",
    [
        ("https://llama.yourcompany.com/v1/completions", "llama"),
    ],
)
def test_detect_model_llama_provider(base_url, api):
    assert detect_provider_from_url(base_url) == api


@pytest.mark.parametrize(
    "base_url,api",
    [
        ("https://api.groq.com/openai/v1", None),
        ("https://api.perplexity.ai/chat/completions", None),
    ],
)
def test_detect_invalid_model_provider(base_url, api):
    assert detect_provider_from_url(base_url) == api


def test_extract_readme_content_existing_md():
    # Arrange
    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda x: x.endswith("README.md")
        with patch("builtins.open", mock_open(read_data="# Test README")):

            # Act
            content = extract_readme_content("/fake/path")

            # Assert
            assert content == "# Test README"


def test_extract_readme_content_existing_rst():
    # Arrange
    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda x: x.endswith("README.rst")
        with patch("builtins.open", mock_open(read_data="Test README")):

            # Act
            content = extract_readme_content("/fake/path")

            # Assert
            assert content == "Test README"


def test_extract_readme_content_no_readme():
    # Arrange
    with patch("os.path.exists", return_value=False):

        # Act
        content = extract_readme_content("/fake/path")

        # Assert
        assert content == "No README.md file"


def test_extract_readme_content_prefer_md():
    # Arrange
    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda x: x.endswith("README.md")
        with patch("builtins.open", mock_open(read_data="# Markdown README")):

            # Act
            content = extract_readme_content("/fake/path")

            # Assert
            assert content == "# Markdown README"
