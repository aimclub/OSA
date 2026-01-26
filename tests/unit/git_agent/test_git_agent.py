import os
import tempfile
from unittest.mock import Mock, patch, ANY

import pytest
from git import Repo, GitCommandError

from osa_tool.analytics.metadata import (
    GitHubMetadataLoader,
    GitverseMetadataLoader,
    GitLabMetadataLoader,
)
from osa_tool.git_agent.git_agent import GitHubAgent, GitverseAgent, GitLabAgent
from osa_tool.utils.utils import parse_folder_name


@pytest.fixture
def temp_clone_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def mock_repo():
    repo = Mock(spec=Repo)
    repo.git = Mock()
    return repo


@pytest.fixture
def git_agent_base_setup(temp_clone_dir, mock_repository_metadata, repo_info, monkeypatch):
    platform, owner, repo_name, repo_url = repo_info

    monkeypatch.setenv("GIT_TOKEN", "fake-token-base-setup")

    with patch.object(GitHubMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitHubAgent(repo_url)

        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent, platform, repo_url, temp_clone_dir


def test_git_agent_initialization(git_agent_base_setup):
    # Arrange
    agent, platform, repo_url, temp_dir = git_agent_base_setup

    # Act / Assert
    assert agent.repo_url == repo_url
    assert agent.token == "fake-token-base-setup"
    assert agent.base_branch == agent.metadata.default_branch
    assert agent.branch_name == "osa_tool"
    assert agent.clone_dir.startswith(temp_dir)


def test_git_agent_clone_repository_success_new(git_agent_base_setup, mock_repo):
    # Arrange
    agent, platform, repo_url, temp_dir = git_agent_base_setup
    clone_path = agent.clone_dir

    # Act
    with patch.object(agent, "_get_auth_url", return_value="https://token@github.com/user/repo.git") as mock_auth:
        with patch.object(agent, "_get_unauth_url", return_value="https://github.com/user/repo.git") as mock_unauth:
            with patch("git.Repo.clone_from") as mock_clone_from:
                mock_clone_from.side_effect = [Exception("fail clone unauth"), mock_repo]

                if os.path.exists(clone_path):
                    os.rmdir(clone_path)

                agent.clone_repository()

                # Assert
                assert mock_clone_from.call_count == 2
                first_call = mock_clone_from.call_args_list[0]
                second_call = mock_clone_from.call_args_list[1]

                assert first_call.kwargs["url"] == mock_unauth.return_value
                assert second_call.kwargs["url"] == mock_auth.return_value

                assert agent.repo == mock_repo


def test_git_agent_clone_repository_success_existing(git_agent_base_setup, temp_clone_dir):
    # Arrange
    agent, platform, repo_url, temp_dir = git_agent_base_setup
    clone_path = agent.clone_dir
    os.makedirs(clone_path, exist_ok=True)
    real_repo = Repo.init(path=clone_path)
    real_repo.config_writer().set_value("user", "name", "Test User").release()
    real_repo.config_writer().set_value("user", "email", "test@example.com").release()

    # Act
    agent.clone_repository()

    # Assert
    assert isinstance(agent.repo, Repo)
    assert agent.repo.working_dir == clone_path


def test_git_agent_clone_repository_failure_git_error(git_agent_base_setup):
    # Arrange
    agent, platform, repo_url, temp_dir = git_agent_base_setup

    # Act / Assert
    with patch("git.Repo.clone_from", side_effect=GitCommandError("clone", "error output")):
        with pytest.raises(Exception, match="Cannot clone the repository"):
            agent.clone_repository()


def test_git_agent_create_and_checkout_branch_new(git_agent_base_setup, mock_repo):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    agent.repo = mock_repo
    mock_repo.heads = ["existing-branch"]
    new_branch = "new-branch"

    # Act
    agent.create_and_checkout_branch(new_branch)

    # Assert
    mock_repo.git.checkout.assert_called_once_with("-b", new_branch)


def test_git_agent_create_and_checkout_branch_exists(git_agent_base_setup, mock_repo):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    agent.repo = mock_repo
    existing_branch = "existing-branch"
    mock_repo.heads = [existing_branch]
    mock_repo.git.reset_mock()

    # Act
    agent.create_and_checkout_branch(existing_branch)

    # Assert
    mock_repo.git.checkout.assert_called_once_with(existing_branch)


def test_git_agent_commit_and_push_changes_success(git_agent_base_setup, mock_repo):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    agent.repo = mock_repo
    agent.fork_url = "https://github.com/user/test-repo.git"
    branch_name = "test-branch"
    commit_msg = "Test commit"

    with patch.object(agent, "_get_auth_url", return_value="https://token@github.com/user/test-repo.git"):
        mock_repo.git.add.return_value = None
        mock_repo.git.commit.return_value = None
        mock_repo.git.push.return_value = None
        mock_repo.git.remote.return_value = None

        # Act
        result = agent.commit_and_push_changes(branch=branch_name, commit_message=commit_msg)

        # Assert
        mock_repo.git.add.assert_called_once_with(".")
        mock_repo.git.commit.assert_called_once_with("-m", commit_msg)
        mock_repo.git.remote.assert_called_once_with("set-url", "origin", agent._get_auth_url(agent.fork_url))
        mock_repo.git.push.assert_called_once_with(
            "--set-upstream", "origin", branch_name, force_with_lease=True, force=False
        )
        assert result is True


def test_git_agent_commit_and_push_changes_nothing_to_commit(git_agent_base_setup, mock_repo):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    agent.repo = mock_repo
    agent.fork_url = "https://github.com/user/test-repo.git"
    branch_name = "test-branch"
    commit_msg = "Test commit"

    mock_repo.git.add.return_value = None
    mock_repo.git.commit.side_effect = GitCommandError("commit", "nothing to commit, working tree clean")

    with patch.object(agent, "_get_auth_url", return_value="https://token@github.com/user/test-repo.git"):
        # Act
        result = agent.commit_and_push_changes(branch=branch_name, commit_message=commit_msg)

        # Assert
        mock_repo.git.add.assert_called_once_with(".")
        mock_repo.git.commit.assert_called_once_with("-m", commit_msg)
        mock_repo.git.push.assert_not_called()
        assert result is False


def test_git_agent_upload_report(git_agent_base_setup, mock_repo, temp_clone_dir):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    agent.repo = mock_repo
    report_filename = "report.pdf"
    report_content = b"fake pdf content"
    report_filepath = os.path.join(temp_clone_dir, report_filename)
    report_branch = "attachments"

    with open(report_filepath, "wb") as f:
        f.write(report_content)

    mock_repo.heads = ["osa_tool", report_branch]
    mock_repo.git.checkout.return_value = None
    mock_repo.git.add.return_value = None
    mock_repo.git.commit.return_value = None
    mock_repo.git.push.return_value = None
    mock_repo.git.remote.return_value = None

    expected_report_path = os.path.join(agent.clone_dir, report_filename)
    os.makedirs(agent.clone_dir, exist_ok=True)
    agent.fork_url = "https://github.com/user/test-repo.git"

    # Act
    with patch.object(
        agent, "_build_report_url", return_value=f"https://fork_url/blob/{report_branch}/{report_filename}"
    ):
        agent.upload_report(report_filename, report_filepath, report_branch=report_branch)

        # Assert
        assert mock_repo.git.checkout.call_count >= 2
        assert os.path.exists(expected_report_path)
        mock_repo.git.add.assert_called()
        mock_repo.git.commit.assert_called()
        mock_repo.git.push.assert_called()
        assert report_filename in agent.pr_report_body


@pytest.fixture
def github_agent_instance(temp_clone_dir, mock_repository_metadata, repo_info, monkeypatch):
    platform, owner, repo_name, repo_url = repo_info
    monkeypatch.setenv("GIT_TOKEN", "fixture-token-github")
    with patch.object(GitHubMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitHubAgent(repo_url)
        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent


def test_github_agent_load_metadata(github_agent_instance, mock_repository_metadata):
    # Arrange / Act / Assert
    assert github_agent_instance.metadata == mock_repository_metadata


def test_github_agent_create_fork_success(github_agent_instance, mock_requests_response_factory, repo_info):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    expected_api_url = f"https://api.github.com/repos/{owner}/{repo_name}/forks"
    expected_fork_html_url = f"https://github.com/user/{repo_name}"
    mock_response = mock_requests_response_factory(status_code=202, json_data={"html_url": expected_fork_html_url})

    # Act
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token_for_env"}):
        with patch("requests.post", return_value=mock_response) as mock_post:
            github_agent_instance.create_fork()

            # Assert
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert expected_api_url in args[0]
            assert kwargs["headers"]["Authorization"].startswith("token")
            assert github_agent_instance.fork_url == expected_fork_html_url


def test_github_agent_create_fork_failure(github_agent_instance, mock_requests_response_factory):
    # Arrange
    mock_response = mock_requests_response_factory(status_code=401, text_data="Bad credentials")

    # Act / Assert
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token_for_env"}):
        with patch("requests.post", return_value=mock_response):
            with pytest.raises(ValueError, match="Failed to create fork."):
                github_agent_instance.create_fork()


def test_github_agent_star_repository_already_starred(github_agent_instance, mock_requests_response_factory, repo_info):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    expected_api_url = f"https://api.github.com/user/starred/{owner}/{repo_name}"
    mock_response_check = mock_requests_response_factory(status_code=204)

    # Act
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token_for_env"}):
        with patch("requests.get", return_value=mock_response_check) as mock_get, patch("requests.put") as mock_put:
            github_agent_instance.star_repository()

            # Assert
            mock_get.assert_called_once_with(expected_api_url, headers=ANY)
            mock_put.assert_not_called()


def test_github_agent_star_repository_success(github_agent_instance, mock_requests_response_factory, repo_info):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    expected_api_url = f"https://api.github.com/user/starred/{owner}/{repo_name}"
    mock_response_check = mock_requests_response_factory(status_code=404)
    mock_response_put = mock_requests_response_factory(status_code=204)

    # Act
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token_for_env"}):
        with (
            patch("requests.get", return_value=mock_response_check) as mock_get,
            patch("requests.put", return_value=mock_response_put) as mock_put,
        ):
            github_agent_instance.star_repository()

            # Assert
            mock_get.assert_called_once_with(expected_api_url, headers=ANY)
            mock_put.assert_called_once_with(expected_api_url, headers=ANY)


@pytest.fixture
def gitlab_agent_instance(temp_clone_dir, mock_repository_metadata, repo_info, monkeypatch):
    platform, owner, repo_name, repo_url = repo_info
    monkeypatch.setenv("GITLAB_TOKEN", "fixture-token-gitlab")
    with patch.object(GitLabMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitLabAgent(repo_url)
        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent


@pytest.mark.parametrize("mock_config_manager", ["gitlab"], indirect=True)
def test_gitlab_agent_create_fork_success(
    gitlab_agent_instance, mock_requests_response_factory, mock_repository_metadata, repo_info, mock_config_manager
):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    expected_project_path = f"{owner}%2F{repo_name}"
    expected_api_url = f"https://gitlab.com/api/v4/projects/{expected_project_path}/fork"

    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"username": "other_user"})
    mock_project_response = mock_requests_response_factory(status_code=200, json_data={"owner": {"id": 123}})
    mock_forks_response = mock_requests_response_factory(status_code=200, json_data=[])
    expected_fork_web_url = f"https://gitlab.com/other_user/{repo_name}"
    mock_fork_response = mock_requests_response_factory(status_code=201, json_data={"web_url": expected_fork_web_url})

    # Act
    with patch.dict(os.environ, {"GITLAB_TOKEN": "any_token_for_env"}):
        with (
            patch(
                "requests.get", side_effect=[mock_user_response, mock_project_response, mock_forks_response]
            ) as mock_get,
            patch("requests.post", return_value=mock_fork_response) as mock_post,
        ):

            gitlab_agent_instance.create_fork()

            # Assert
            assert mock_get.call_count == 3
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert expected_api_url == args[0]
            assert kwargs["headers"]["Authorization"].startswith("Bearer")
            assert gitlab_agent_instance.fork_url == expected_fork_web_url


@pytest.fixture
def gitverse_agent_instance(temp_clone_dir, mock_repository_metadata, repo_info, monkeypatch):
    platform, owner, repo_name, repo_url = repo_info
    monkeypatch.setenv("GITVERSE_TOKEN", "fixture-token-gitverse")
    with patch.object(GitverseMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitverseAgent(repo_url)
        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent


def test_gitverse_agent_create_fork_success(gitverse_agent_instance, mock_requests_response_factory, repo_info):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"login": "other_user"})
    mock_fork_check_response = mock_requests_response_factory(status_code=404)
    mock_fork_response = mock_requests_response_factory(
        status_code=201, json_data={"full_name": f"other_user/{repo_name}"}
    )

    with patch.dict(os.environ, {"GITVERSE_TOKEN": "any_token_for_env"}):
        with (
            patch("requests.get", side_effect=[mock_user_response, mock_fork_check_response]) as mock_get,
            patch("requests.post", return_value=mock_fork_response) as mock_post,
        ):

            # Act
            gitverse_agent_instance.create_fork()

            # Assert
            assert mock_get.call_count == 2
            mock_get.assert_any_call(
                "https://api.gitverse.ru/user",
                headers=ANY,
            )
            mock_get.assert_any_call(
                f"https://api.gitverse.ru/repos/other_user/{repo_name}",
                headers=ANY,
            )
            mock_post.assert_called_once()
            assert gitverse_agent_instance.fork_url == f"https://gitverse.ru/other_user/{repo_name}"


def test_gitverse_agent_star_repository_success(gitverse_agent_instance, mock_requests_response_factory, repo_info):
    # Arrange
    mock_response_check = mock_requests_response_factory(status_code=404)
    mock_response_put = mock_requests_response_factory(status_code=204)

    with patch.dict(os.environ, {"GITVERSE_TOKEN": "any_token_for_env"}):
        with (
            patch("requests.get", return_value=mock_response_check) as mock_get,
            patch("requests.put", return_value=mock_response_put) as mock_put,
        ):

            # Act
            gitverse_agent_instance.star_repository()

            # Assert
            mock_get.assert_called_once()
            mock_put.assert_called_once()


def test_gitverse_agent_star_repository_already_starred(
    gitverse_agent_instance, mock_requests_response_factory, repo_info
):
    # Arrange
    mock_response_check = mock_requests_response_factory(status_code=204)

    with patch.dict(os.environ, {"GITVERSE_TOKEN": "any_token_for_env"}):
        with patch("requests.get", return_value=mock_response_check) as mock_get, patch("requests.put") as mock_put:

            # Act
            gitverse_agent_instance.star_repository()

            # Assert
            mock_get.assert_called_once()
            mock_put.assert_not_called()
