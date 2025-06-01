from unittest.mock import Mock, patch

import pytest

from osa_tool.github_agent.github_agent import GithubAgent


@pytest.fixture
def github_agent():
    agent = GithubAgent("https://github.com/username/repo")
    agent.token = "dummy_token"
    agent.fork_url = "https://github.com/fork/repo"
    return agent


@pytest.fixture
def about_content():
    return {
        "description": "Test description",
        "homepage": "https://test.com",
        "topics": ["test", "topics"],
    }


def test_update_about_section_success(github_agent, about_content):
    with patch("requests.patch") as mock_patch, patch("requests.put") as mock_put:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_patch.return_value = mock_response
        mock_put.return_value = mock_response

        github_agent.update_about_section(about_content)

        assert mock_patch.call_count == 2
        assert mock_put.call_count == 2


def test_update_about_section_no_token(github_agent, about_content):
    github_agent.token = None
    with pytest.raises(ValueError, match="GitHub token is required"):
        github_agent.update_about_section(about_content)


def test_update_about_section_no_fork(github_agent, about_content):
    github_agent.fork_url = None
    with pytest.raises(ValueError, match="Fork URL is not set"):
        github_agent.update_about_section(about_content)


def test_update_about_section_api_failure(github_agent, about_content):
    with patch("requests.patch") as mock_patch, patch("requests.put") as mock_put:
        mock_response = Mock()
        mock_response.status_code = 400
        mock_patch.return_value = mock_response
        mock_put.return_value = mock_response

        github_agent.update_about_section(about_content)

        assert mock_patch.call_count == 2
        assert mock_put.call_count == 2


def test_update_about_section_content_format(github_agent, about_content):
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
