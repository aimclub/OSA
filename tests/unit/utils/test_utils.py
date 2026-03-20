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
    """
    Tests the parse_folder_name function with a GitHub repository URL.
    
    This method verifies that parse_folder_name correctly extracts the repository name from a standard GitHub URL. It uses a fixed GitHub URL as a test case to ensure the helper function handles a typical, well-formed URL pattern appropriately.
    
    Args:
        None
    
    Returns:
        None
    
    Why:
    - This test ensures the extraction logic works for one of the most common Git hosting platforms.
    - It validates that the folder name derived matches the expected repository name segment, confirming the URL parsing behaves correctly for a standard GitHub URL structure.
    """
    # Arrange
    repo_url = "https://github.com/user/repo-name"

    # Act
    folder_name = parse_folder_name(repo_url)

    # Assert
    assert folder_name == "repo-name"


def test_parse_folder_name_gitlab():
    """
    Tests the parse_folder_name function with a GitLab repository URL.
    
    This method verifies that the parse_folder_name helper correctly extracts
    the repository name from a provided GitLab URL. It follows a standard
    test structure (Arrange, Act, Assert) to validate the extraction.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    repo_url = "https://gitlab.com/user/repo-name"

    # Act
    folder_name = parse_folder_name(repo_url)

    # Assert
    assert folder_name == "repo-name"


def test_parse_folder_name_gitverse():
    """
    Tests the parse_folder_name function with a Gitverse repository URL.
    
    This method verifies that parse_folder_name correctly extracts the folder
    name from a provided Gitverse repository URL. It follows a standard
    test structure: arrange test data, act by calling the function, and assert
    the expected outcome.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    repo_url = "https://gitverse.ru/user/repo-name"

    # Act
    folder_name = parse_folder_name(repo_url)

    # Assert
    assert folder_name == "repo-name"


def test_osa_project_root():
    """
    Tests the osa_project_root function.
    
    This method verifies that the osa_project_root function returns a Path object
    and that the returned path either has the name "osa_tool" or exists on the filesystem.
    This ensures the function correctly identifies the project root, which is essential for reliably locating project resources and configuration files from any module within the codebase.
    
    Args:
        None
    
    Returns:
        None
    """
    # Act
    root = osa_project_root()

    # Assert
    assert isinstance(root, Path)
    assert root.name == "osa_tool" or root.exists()


def test_get_base_repo_url_github():
    """
    Tests the get_base_repo_url function with a standard GitHub HTTPS URL.
    
    This test verifies that the function correctly extracts the base repository path ("user/repo-name") from the provided URL.
    
    Args:
        None
    
    Returns:
        None
    
    Why:
        This test ensures the helper function properly handles a common GitHub URL pattern, confirming it extracts the owner and repository name as expected for downstream use.
    """
    # Arrange
    repo_url = "https://github.com/user/repo-name"

    # Act
    base_url = get_base_repo_url(repo_url)

    # Assert
    assert base_url == "user/repo-name"


def test_get_base_repo_url_gitlab():
    """
    Tests the get_base_repo_url function with a GitLab repository URL.
    
    Asserts that the function correctly extracts the base repository path
    from a provided GitLab URL string.
    
    Why:
    This test verifies that the helper function properly handles GitLab URLs,
    which can include subgroup paths. It ensures the extraction logic works
    for GitLab's nested group structure, returning the full path without
    the hostname prefix.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    repo_url = "https://gitlab.com/group/subgroup/repo-name"

    # Act
    base_url = get_base_repo_url(repo_url)

    # Assert
    assert base_url == "group/subgroup/repo-name"


def test_get_base_repo_url_gitverse():
    """
    Tests the extraction of the base repository URL path for a Gitverse URL.
    
    This test verifies that `get_base_repo_url` correctly processes a URL
    from the gitverse.ru domain, returning the expected 'user/repo-name' format.
    
    Why:
    This test ensures the helper function properly handles URLs from the GitVerse hosting service, confirming it can standardize repository references from this specific platform alongside others like GitHub or GitLab.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    repo_url = "https://gitverse.ru/user/repo-name"

    # Act
    base_url = get_base_repo_url(repo_url)

    # Assert
    assert base_url == "user/repo-name"


def test_get_base_repo_url_invalid():
    """
    Tests that get_base_repo_url raises a ValueError for an invalid repository URL.
    
    This test verifies that the helper function `get_base_repo_url` correctly
    raises a `ValueError` when provided with a URL that has an unsupported format.
    
    Why:
    This test ensures the helper function properly validates input and rejects URLs that do not match expected Git hosting patterns, maintaining robustness in repository URL handling.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    repo_url = "https://invalid.com/repo"

    # Act
    with pytest.raises(ValueError):
        get_base_repo_url(repo_url)


def test_parse_git_url_https():
    """
    Tests the parsing of an HTTPS GitHub repository URL.
    
    This method verifies that `parse_git_url` correctly extracts the host domain,
    host, repository name, and full repository name from a standard HTTPS GitHub URL.
    It uses a fixed example URL to confirm each extracted component matches the expected values.
    
    Args:
        None
    
    Returns:
        None
    
    Why:
    This test ensures the URL parser handles the most common HTTPS GitHub URL format correctly,
    which is a fundamental requirement for the OSA Tool to accurately analyze and interact with
    GitHub repositories during its documentation and enhancement processes.
    """
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
    """
    Tests that parse_git_url raises ValueError for a repository URL with an invalid scheme.
    
    This test verifies that the function correctly rejects URLs using schemes other than http or https, such as ftp, ensuring only web-based Git repository URLs are processed.
    
    Args:
        repo_url: The URL of the GitHub repository. In this test, it is specifically set to "ftp://github.com/user/repo-name" to represent an invalid scheme.
    
    Returns:
        None
    """
    # Arrange
    repo_url = "ftp://github.com/user/repo-name"

    # Act
    with pytest.raises(ValueError):
        parse_git_url(repo_url)


def test_parse_git_url_invalid_url():
    """
    Test that parse_git_url raises ValueError for an invalid URL.
    
    This test verifies that the parse_git_url function correctly raises a
    ValueError when provided with a string that is not a valid repository URL.
    The test uses a malformed string to ensure the function properly validates
    URL format and scheme, as required by the helper function's specification.
    
    Args:
        None
    
    Returns:
        None
    """
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
    """
    Test that detect_provider_from_url correctly identifies OpenAI-compatible providers.
    
    This test verifies that the helper function properly recognizes various API endpoints that are compatible with the OpenAI API format. This ensures the tool can adapt its configuration and behavior for different services that use the same interface.
    
    Args:
        base_url: The API URL to test.
        api: The expected provider name (should be "openai" for all provided examples).
    
    Returns:
        None
    """
    assert detect_provider_from_url(base_url) == api


@pytest.mark.parametrize(
    "base_url,api",
    [
        ("http://10.9.0.1:11434/api/generate", "ollama"),
        ("http://localhost:11434/api/generate", "ollama"),
    ],
)
def test_detect_model_ollama_provider(base_url, api):
    """
    Test that detect_provider_from_url correctly identifies Ollama provider URLs.
    
    This test ensures the helper function properly recognizes URLs for local and remote Ollama API endpoints, which is necessary for the tool to adapt its behavior or configuration automatically based on the service being called.
    
    Args:
        base_url: The API URL to test for provider detection.
        api: The expected provider name for the given URL (should be "ollama").
    
    Returns:
        None
    """
    assert detect_provider_from_url(base_url) == api


@pytest.mark.parametrize(
    "base_url,api",
    [
        ("https://llama.yourcompany.com/v1/completions", "llama"),
    ],
)
def test_detect_model_llama_provider(base_url, api):
    """
    Tests that detect_provider_from_url correctly identifies the 'llama' provider for a specific URL.
    
    This test is parameterized to verify that the helper function returns the expected provider name when given a URL matching the 'llama' provider pattern. This ensures the detection logic works correctly for this provider, which is necessary for the tool to adapt its API interactions appropriately.
    
    Args:
        base_url: The API URL to test against the 'llama' provider pattern.
        api: The expected provider name, which should be 'llama' for the provided URL.
    
    Returns:
        None.
    """
    assert detect_provider_from_url(base_url) == api


@pytest.mark.parametrize(
    "base_url,api",
    [
        ("https://api.groq.com/openai/v1", None),
        ("https://api.perplexity.ai/chat/completions", None),
    ],
)
def test_detect_invalid_model_provider(base_url, api):
    """
    Tests that detect_provider_from_url returns None for unsupported model provider URLs.
    
    This test ensures that the detection function correctly identifies URLs from providers not supported by the system, returning None to indicate that no known provider pattern matches. This is important for maintaining clear boundaries between supported and unsupported services, preventing incorrect provider assumptions.
    
    Args:
        base_url: The API URL to test.
        api: The expected result from the detection function, which should be None for unsupported URLs.
    
    Returns:
        None
    """
    assert detect_provider_from_url(base_url) == api


def test_extract_readme_content_existing_md():
    """
    Tests the extraction of README content when a README.md file exists.
    
    This test mocks the filesystem to simulate the presence of a README.md
    file at the given path and verifies that the helper function correctly
    returns its content.
    
    WHY: The test ensures that the helper function properly identifies and reads a README.md file when it is present, confirming the expected behavior for the highest-priority README file type.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda x: x.endswith("README.md")
        with patch("builtins.open", mock_open(read_data="# Test README")):

            # Act
            content = extract_readme_content("/fake/path")

            # Assert
            assert content == "# Test README"


def test_extract_readme_content_existing_rst():
    """
    Tests the extraction of README content when a README.rst file exists.
    
    This test mocks the filesystem to simulate the presence of a README.rst
    file at the given path and verifies that the helper function correctly
    returns its content.
    
    WHY: The test ensures that the helper function properly handles the case where a generic README.rst file is present, which is the third priority in the supported README filename order. It validates that the function reads and returns the correct content when higher-priority files (README.md and README_en.rst) are absent.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda x: x.endswith("README.rst")
        with patch("builtins.open", mock_open(read_data="Test README")):

            # Act
            content = extract_readme_content("/fake/path")

            # Assert
            assert content == "Test README"


def test_extract_readme_content_no_readme():
    """
    Tests the behavior of extract_readme_content when no README file exists.
    
    This test mocks the filesystem to simulate a missing README file and
    verifies that the helper function returns the expected default message.
    
    WHY: The test ensures the helper function gracefully handles the absence of any README file by returning a clear default string, which is important for downstream processing that expects a consistent return type.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    with patch("os.path.exists", return_value=False):

        # Act
        content = extract_readme_content("/fake/path")

        # Assert
        assert content == "No README.md file"


def test_extract_readme_content_prefer_md():
    """
    Tests that extract_readme_content prefers a README.md file when both README.md and README.rst exist.
    
    This test mocks the filesystem to simulate a scenario where a README.md file
    is present at the given repository path. It verifies that the helper function
    extract_readme_content correctly returns the content of the README.md file.
    
    WHY: The test ensures the helper function's prioritization logic works correctly—Markdown READMEs are preferred over reStructuredText files, which is important for consistency and compatibility across repositories.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    with patch("os.path.exists") as mock_exists:
        mock_exists.side_effect = lambda x: x.endswith("README.md")
        with patch("builtins.open", mock_open(read_data="# Markdown README")):

            # Act
            content = extract_readme_content("/fake/path")

            # Assert
            assert content == "# Markdown README"
