from unittest.mock import Mock, patch

import pytest

from osa_tool.git_agent.git_agent import GitAgent


@pytest.fixture
def github_agent():
    """
    Create and configure a GitAgent instance for a GitHub repository.
    
    This function initializes a GitAgent with a specified repository URL and
    branch, sets a placeholder authentication token, and assigns a fork URL.
    The configured agent is then returned for use in further operations.
    
    Returns:
        GitAgent: A configured GitAgent instance pointing to the repository
        and fork URL.
    """
    agent = GitAgent("https://github.com/username/repo", repo_branch_name="main")
    agent.token = "dummy_token"
    agent.fork_url = "https://github.com/fork/repo"
    return agent


@pytest.fixture
def about_content():
    """
    Return static metadata for the about page.
    
    Returns:
        dict: A dictionary containing package metadata with the following keys:
            description (str): A short description of the content.
            homepage (str): URL of the homepage.
            topics (list[str]): List of topic tags.
    """
    return {
        "description": "Test description",
        "homepage": "https://test.com",
        "topics": ["test", "topics"],
    }


def test_update_about_section_success(github_agent, about_content):
    """
    Test that updating the about section succeeds.
    
    Parameters
    ----------
    github_agent
        The GitHub agent instance used to perform the update.
    about_content
        The content to be set in the about section.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the update
        operation triggers the expected HTTP calls and receives a
        successful status code.
    """
    with patch("requests.patch") as mock_patch, patch("requests.put") as mock_put:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response
        mock_put.return_value = mock_response

        github_agent.update_about_section(about_content)

        assert mock_patch.call_count == 2
        assert mock_put.call_count == 2


def test_update_about_section_no_token(github_agent, about_content):
    """
    Test that updating the 'About' section without a GitHub token raises a ValueError.
    
    Parameters
    ----------
    github_agent
        The GitHub agent instance used to perform repository operations.
    about_content
        The content to be used for the 'About' section update.
    
    Raises
    ------
    ValueError
        If the GitHub token is missing, a ValueError is expected.
    
    Returns
    -------
    None
        This function does not return a value; it asserts exception behavior.
    """
    github_agent.token = None
    with pytest.raises(ValueError, match="Github token is required to update repository's 'About' section."):
        github_agent.update_about_section(about_content)


def test_update_about_section_no_fork(github_agent, about_content):
    """
    Test that `update_about_section` raises a `ValueError` when the fork URL is not set.
    
    Parameters
    ----------
    github_agent
        The GitHub agent instance whose `fork_url` attribute is manipulated for the test.
    about_content
        The content string that would normally be passed to `update_about_section`.
    
    Returns
    -------
    None
        This test function does not return a value; it asserts that a `ValueError` is raised.
    """
    github_agent.fork_url = None
    with pytest.raises(ValueError, match="Fork URL is not set"):
        github_agent.update_about_section(about_content)


def test_update_about_section_api_failure(github_agent, about_content):
    """
    Test that the `update_about_section` method handles API failures correctly.
    
    Parameters
    ----------
    github_agent
        The GitHub agent instance used to update the about section.
    about_content
        The content to be used for the about section.
    
    Returns
    -------
    None
    
    This test patches `requests.patch` and `requests.put` to return a 400 status code, simulating a failure from the GitHub API. It then calls `github_agent.update_about_section(about_content)` and verifies that both the PATCH and PUT requests were attempted twice, ensuring that the method retries the update when the API responds with an error.
    """
    with patch("requests.patch") as mock_patch, patch("requests.put") as mock_put:
        mock_response = Mock()
        mock_response.status_code = 400
        mock_patch.return_value = mock_response
        mock_put.return_value = mock_response

        github_agent.update_about_section(about_content)

        assert mock_patch.call_count == 2
        assert mock_put.call_count == 2


def test_update_about_section_content_format(github_agent, about_content):
    """
    Test that the GitHub agent correctly formats the payloads for updating the
    about section of a repository.
    
    The test patches the `requests.patch` and `requests.put` functions to
    intercept HTTP calls made by `github_agent.update_about_section`. It then
    verifies that:
    
    * Two PATCH requests are issued, each containing the keys `description` and
      `homepage` in their JSON payload.
    * Two PUT requests are issued, each containing the key `names` in their JSON
      payload.
    
    This ensures that the agent constructs the request bodies in the expected
    format before sending them to the GitHub API.
    
    Parameters
    ----------
    github_agent
        The GitHub agent instance that provides the `update_about_section`
        method.
    about_content
        The content object passed to `update_about_section`, representing the
        new about section data.
    
    Returns
    -------
    None
    """
    with patch("requests.patch") as mock_patch, patch("requests.put") as mock_put:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response
        mock_put.return_value = mock_response

        github_agent.update_about_section(about_content)

        patch_calls = mock_patch.call_args_list
        assert len(patch_calls) == 2
        for call in patch_calls:
            assert "description" in call[1]["json"]
            assert "homepage" in call[1]["json"]

        put_calls = mock_put.call_args_list
        assert len(put_calls) == 2
        for call in put_calls:
            assert "names" in call[1]["json"]
