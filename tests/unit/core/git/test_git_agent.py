import os
import tempfile
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch, ANY, MagicMock

import pytest
from git import Repo, GitCommandError, InvalidGitRepositoryError

from osa_tool.core.git.git_agent import GitHubAgent, GitverseAgent, GitLabAgent, SourceCraftAgent, LocalGitAgent
from osa_tool.core.git.metadata import (
    GitHubMetadataLoader,
    GitverseMetadataLoader,
    GitLabMetadataLoader,
    SourceCraftMetadataLoader,
)
from osa_tool.utils.utils import parse_date_argument, parse_folder_name


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
    # isolate from a real .env on disk: GitAgent calls load_dotenv(override=True), which
    # would otherwise clobber the fake token above with the developer's real token
    monkeypatch.setattr("osa_tool.core.git.git_agent.load_dotenv", lambda *a, **k: None)

    with patch.object(GitHubMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitHubAgent(repo_url)

        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent, platform, repo_url, temp_clone_dir


def test_git_agent_initialization(git_agent_base_setup):
    # Arrange
    agent, platform, repo_url, temp_dir = git_agent_base_setup

    # Assert
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
    git_error = GitCommandError("clone", 128, b"fatal: repository not found")

    # Act
    with patch("git.Repo.clone_from", side_effect=git_error):
        with pytest.raises(Exception, match=r"Git operation 'cloning repository.*' failed"):
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
    # Assert
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

    # Act
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token_for_env"}):
        with patch("requests.post", return_value=mock_response):
            with pytest.raises(ValueError, match=r"API operation 'creating GitHub fork' failed with status 401"):
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
            mock_get.assert_called_once_with(expected_api_url, headers=ANY, timeout=ANY)
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
            mock_get.assert_called_once_with(expected_api_url, headers=ANY, timeout=ANY)
            mock_put.assert_called_once_with(expected_api_url, headers=ANY, timeout=ANY)


def test_github_agent_star_repository_failure_non_critical(
    github_agent_instance, mock_requests_response_factory, repo_info
):
    # Arrange
    # 403 - does not fail the execution
    mock_response_check = mock_requests_response_factory(status_code=403, text_data="Forbidden")
    mock_response_star = mock_requests_response_factory(status_code=204)

    # Act
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token_for_env"}):
        with (
            patch("requests.get", return_value=mock_response_check) as mock_get,
            patch("requests.put", return_value=mock_response_star) as mock_put,
        ):
            github_agent_instance.star_repository()
            # Assert
            mock_get.assert_called_once()
            mock_put.assert_called_once()


def test_github_agent_create_pull_request_update_reports(
    github_agent_instance, mock_repo, mock_requests_response_factory, repo_info
):
    # Arrange - existing PR already has an old report; new report must be merged in
    platform, owner, repo_name, repo_url = repo_info
    github_agent_instance.repo = mock_repo
    github_agent_instance.fork_url = repo_url
    github_agent_instance.base_branch = "main"
    github_agent_instance.branch_name = "osa_tool"

    old_report = "Generated report - [old.pdf](https://example.com/old.pdf)"
    new_report = "Generated report - [new.pdf](https://example.com/new.pdf)"
    github_agent_instance.pr_report_body = f"\n{new_report}\n"

    existing_pr_body = f"User content\n\n{old_report}{github_agent_instance.agent_signature}"
    mock_get_response = mock_requests_response_factory(
        status_code=200, json_data=[{"number": 42, "body": existing_pr_body}]
    )
    mock_patch_response = mock_requests_response_factory(status_code=200, json_data={})

    # Act
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token"}):
        with (
            patch("osa_tool.core.git.git_agent.requests.get", return_value=mock_get_response),
            patch("osa_tool.core.git.git_agent.requests.patch", return_value=mock_patch_response) as mock_patch,
        ):
            github_agent_instance.create_pull_request(changes=True)

    # Assert
    mock_patch.assert_called_once()
    sent_body = mock_patch.call_args.kwargs["json"]["body"]
    assert old_report in sent_body
    assert new_report in sent_body
    assert github_agent_instance.agent_signature in sent_body


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


@pytest.mark.parametrize("mock_config_manager", ["gitlab"], indirect=True)
def test_gitlab_agent_create_pull_request_update_reports(
    gitlab_agent_instance, mock_repo, mock_requests_response_factory, repo_info
):
    # Arrange - existing MR already has an old report; new report must be merged in
    platform, owner, repo_name, repo_url = repo_info
    gitlab_agent_instance.repo = mock_repo
    gitlab_agent_instance.fork_url = repo_url
    gitlab_agent_instance.base_branch = "main"
    gitlab_agent_instance.branch_name = "osa_tool"

    old_report = "Generated report - [old.pdf](https://example.com/old.pdf)"
    new_report = "Generated report - [new.pdf](https://example.com/new.pdf)"
    gitlab_agent_instance.pr_report_body = f"\n{new_report}\n"

    existing_mr_body = f"User content\n\n{old_report}{gitlab_agent_instance.agent_signature}"

    mock_project_response = mock_requests_response_factory(status_code=200, json_data={"id": 456})
    mock_mr_list_response = mock_requests_response_factory(
        status_code=200, json_data=[{"iid": 7, "id": 7, "description": existing_mr_body}]
    )
    mock_put_response = mock_requests_response_factory(status_code=200, json_data={})

    # Act
    with patch.dict(os.environ, {"GITLAB_TOKEN": "any_token"}):
        with (
            patch(
                "osa_tool.core.git.git_agent.requests.get",
                side_effect=[mock_project_response, mock_mr_list_response],
            ),
            patch("osa_tool.core.git.git_agent.requests.put", return_value=mock_put_response) as mock_put,
        ):
            gitlab_agent_instance.create_pull_request(changes=True)

    # Assert
    mock_put.assert_called_once()
    sent_description = mock_put.call_args.kwargs["json"]["description"]
    assert old_report in sent_description
    assert new_report in sent_description
    assert gitlab_agent_instance.agent_signature in sent_description


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
                timeout=ANY,
            )
            mock_get.assert_any_call(
                f"https://api.gitverse.ru/repos/other_user/{repo_name}",
                headers=ANY,
                timeout=ANY,
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


@pytest.fixture
def sourcecraft_agent_instance(temp_clone_dir, mock_repository_metadata, repo_info, monkeypatch):
    platform, owner, repo_name, repo_url = repo_info
    monkeypatch.setenv("SOURCECRAFT_TOKEN", "fixture-token-sourcecraft")
    # isolate from a real .env on disk (see git_agent_base_setup): load_dotenv(override=True)
    # would otherwise replace the fixture token with the developer's real one
    monkeypatch.setattr("osa_tool.core.git.git_agent.load_dotenv", lambda *a, **k: None)
    with patch("osa_tool.core.git.git_agent.SourceCraftMetadataLoader", create=True) as mock_loader:
        mock_loader.load_data.return_value = mock_repository_metadata
        agent = SourceCraftAgent(repo_url)
        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_create_fork_success(sourcecraft_agent_instance, mock_requests_response_factory, repo_info):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    expected_api_url = f"https://api.sourcecraft.tech/repos/{owner}/{repo_name}/fork"
    expected_fork_url = f"https://sourcecraft.dev/other_user/{repo_name}"

    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"username": "other_user"})
    mock_fork_response = mock_requests_response_factory(
        status_code=201, json_data={"web_url": expected_fork_url, "id": 42}
    )

    # Act
    with patch.dict(os.environ, {"SOURCECRAFT_TOKEN": "any_token"}):
        with (
            patch("requests.get", return_value=mock_user_response),
            patch("requests.post", return_value=mock_fork_response) as mock_post,
        ):
            sourcecraft_agent_instance.create_fork()

            # Assert
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert expected_api_url in args[0]
            assert kwargs["headers"]["Authorization"].startswith("Bearer")
            assert sourcecraft_agent_instance.fork_url == expected_fork_url
            assert sourcecraft_agent_instance.fork_id == 42


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_create_fork_self_owned(
    sourcecraft_agent_instance, mock_requests_response_factory, repo_info
):
    # Arrange - user is already the owner, no fork should be created
    platform, owner, repo_name, repo_url = repo_info
    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"username": owner})

    # Act
    with patch.dict(os.environ, {"SOURCECRAFT_TOKEN": "any_token"}):
        with (
            patch("requests.get", return_value=mock_user_response),
            patch("requests.post") as mock_post,
        ):
            sourcecraft_agent_instance.create_fork()

            # Assert
            mock_post.assert_not_called()
            assert sourcecraft_agent_instance.fork_url == repo_url


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_create_fork_failure(sourcecraft_agent_instance, mock_requests_response_factory):
    # Arrange
    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"username": "other_user"})
    mock_fork_response = mock_requests_response_factory(status_code=401, text_data="Unauthorized")

    # Act & Assert
    with patch.dict(os.environ, {"SOURCECRAFT_TOKEN": "any_token"}):
        with (
            patch("requests.get", return_value=mock_user_response),
            patch("requests.post", return_value=mock_fork_response),
        ):
            with pytest.raises(ValueError, match=r"API operation 'creating SourceCraft fork' failed"):
                sourcecraft_agent_instance.create_fork()


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_star_repository_noop(sourcecraft_agent_instance):
    # SourceCraft has no starring API - must not call any HTTP endpoint
    with patch("requests.put") as mock_put, patch("requests.get") as mock_get:
        sourcecraft_agent_instance.star_repository()

        # Assert
        mock_put.assert_not_called()
        mock_get.assert_not_called()


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_create_pull_request_new(
    sourcecraft_agent_instance, mock_repo, mock_requests_response_factory, repo_info
):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    sourcecraft_agent_instance.repo = mock_repo
    sourcecraft_agent_instance.fork_url = repo_url
    mock_repo.head.commit.message = "Test commit"
    sourcecraft_agent_instance.base_branch = "main"
    sourcecraft_agent_instance.branch_name = "osa_tool"

    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"username": "bot_user"})
    mock_list_response = mock_requests_response_factory(status_code=200, json_data={"pull_requests": []})
    mock_create_response = mock_requests_response_factory(status_code=201, json_data={"slug": "pr-1"})

    # Act
    with patch.dict(os.environ, {"SOURCECRAFT_TOKEN": "any_token"}):
        with patch("requests.get", side_effect=[mock_user_response, mock_list_response]):
            with patch("requests.post", return_value=mock_create_response) as mock_post:
                with patch.object(sourcecraft_agent_instance, "get_attachment_branch_files", return_value=[]):
                    sourcecraft_agent_instance.create_pull_request(changes=True)

                    # Assert
                    mock_post.assert_called_once()
                    _, kwargs = mock_post.call_args
                    assert kwargs["json"]["source_branch"] == "osa_tool"
                    assert kwargs["json"]["target_branch"] == "main"
                    assert kwargs["json"]["publish"] is True


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_create_pull_request_new_with_reports(
    sourcecraft_agent_instance, mock_repo, mock_requests_response_factory, repo_info
):
    # Arrange - new PR, attachment branch has one PDF - link must appear in PR description
    platform, owner, repo_name, repo_url = repo_info
    sourcecraft_agent_instance.repo = mock_repo
    sourcecraft_agent_instance.fork_url = repo_url
    mock_repo.head.commit.message = "Test commit"
    sourcecraft_agent_instance.base_branch = "main"
    sourcecraft_agent_instance.branch_name = "osa_tool"

    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"username": "bot_user"})
    mock_list_response = mock_requests_response_factory(status_code=200, json_data={"pull_requests": []})
    mock_create_response = mock_requests_response_factory(status_code=201, json_data={"slug": "pr-2"})

    # Act
    with patch.dict(os.environ, {"SOURCECRAFT_TOKEN": "any_token"}):
        with patch("requests.get", side_effect=[mock_user_response, mock_list_response]):
            with patch("requests.post", return_value=mock_create_response) as mock_post:
                with patch.object(
                    sourcecraft_agent_instance, "get_attachment_branch_files", return_value=["report.pdf"]
                ):
                    sourcecraft_agent_instance.create_pull_request(changes=True)

                    # Assert — report link included in PR description
                    mock_post.assert_called_once()
                    _, kwargs = mock_post.call_args
                    assert "Generated report" in kwargs["json"]["description"]
                    assert "report.pdf" in kwargs["json"]["description"]


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_create_pull_request_dedup(
    sourcecraft_agent_instance, mock_repo, mock_requests_response_factory, repo_info
):
    # Arrange - existing PR found, no new reports - must not POST a new PR
    platform, owner, repo_name, repo_url = repo_info
    sourcecraft_agent_instance.repo = mock_repo
    mock_repo.head.commit.message = "Test commit"
    sourcecraft_agent_instance.base_branch = "main"
    sourcecraft_agent_instance.branch_name = "osa_tool"

    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"username": "bot_user"})
    mock_list_response = mock_requests_response_factory(
        status_code=200, json_data={"pull_requests": [{"slug": "pr-42", "description": ""}]}
    )

    # Act
    with patch.dict(os.environ, {"SOURCECRAFT_TOKEN": "any_token"}):
        with patch("requests.get", side_effect=[mock_user_response, mock_list_response]):
            with patch("requests.post") as mock_post:
                with patch("requests.patch") as mock_patch:
                    sourcecraft_agent_instance.create_pull_request(changes=True)

                    # Assert - no new PR created, no unnecessary PATCH
                    mock_post.assert_not_called()
                    mock_patch.assert_not_called()


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_create_pull_request_update_reports(
    sourcecraft_agent_instance, mock_repo, mock_requests_response_factory, repo_info
):
    # Arrange - existing PR with old report, new report in pr_report_body - PATCH with merged reports
    platform, owner, repo_name, repo_url = repo_info
    sourcecraft_agent_instance.repo = mock_repo
    mock_repo.head.commit.message = "Test commit"
    sourcecraft_agent_instance.base_branch = "main"
    sourcecraft_agent_instance.branch_name = "osa_tool"
    sourcecraft_agent_instance.pr_report_body = "\nGenerated report - [report_new.pdf](https://example.com/new)\n"

    old_description = "Previous description\n\nGenerated report - [report_old.pdf](https://example.com/old)"
    mock_user_response = mock_requests_response_factory(status_code=200, json_data={"username": "bot_user"})
    mock_list_response = mock_requests_response_factory(
        status_code=200,
        json_data={"pull_requests": [{"slug": "pr-42", "description": old_description}]},
    )
    mock_update_response = mock_requests_response_factory(status_code=200, json_data={"slug": "pr-42"})

    # Act
    with patch.dict(os.environ, {"SOURCECRAFT_TOKEN": "any_token"}):
        with patch("requests.get", side_effect=[mock_user_response, mock_list_response]):
            with patch("requests.post") as mock_post:
                with patch("requests.patch", return_value=mock_update_response) as mock_patch:
                    sourcecraft_agent_instance.create_pull_request(changes=True)

                    # Assert - no new PR, description updated with both report links
                    mock_post.assert_not_called()
                    mock_patch.assert_called_once()
                    patched_description = mock_patch.call_args.kwargs["json"]["description"]
                    assert "report_old.pdf" in patched_description
                    assert "report_new.pdf" in patched_description


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_update_about_section(sourcecraft_agent_instance, mock_requests_response_factory, repo_info):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    sourcecraft_agent_instance.fork_url = repo_url
    mock_response = mock_requests_response_factory(status_code=200, json_data={})

    # Act
    with patch.dict(os.environ, {"SOURCECRAFT_TOKEN": "any_token"}):
        with patch("requests.patch", return_value=mock_response) as mock_patch:
            sourcecraft_agent_instance.update_about_section({"description": "Test description"})

            # Assert - called twice: once for base repo, once for fork
            assert mock_patch.call_count == 2
            for call in mock_patch.call_args_list:
                _, kwargs = call
                assert kwargs["json"]["description"] == "Test description"


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_build_auth_url(sourcecraft_agent_instance, repo_info):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info

    # Act
    auth_url = sourcecraft_agent_instance._build_auth_url(repo_url)

    # Assert
    assert auth_url.startswith("https://git:")
    assert "git.sourcecraft.dev" in auth_url
    assert auth_url.endswith(".git")
    assert "fixture-token-sourcecraft" in auth_url


@pytest.mark.parametrize("mock_config_manager", ["sourcecraft"], indirect=True)
def test_sourcecraft_agent_build_report_url(sourcecraft_agent_instance, repo_info):
    # Arrange
    platform, owner, repo_name, repo_url = repo_info
    sourcecraft_agent_instance.fork_url = repo_url

    # Act
    report_url = sourcecraft_agent_instance._build_report_url("attachments", "report.pdf")

    # Assert
    assert "/browse/" in report_url
    assert "?rev=" in report_url
    assert "attachments" in report_url
    assert "report.pdf" in report_url


@patch("osa_tool.core.git.git_agent.Repo")
@patch("osa_tool.core.git.metadata.Repo")
@patch.object(LocalGitAgent, "_clone_chosen_branch")
@patch.object(LocalGitAgent, "_clone_default_branch")
def test_local_git_agent_cloning(
    mock_clone_default_branch, mock_clone_chosen_branch, mock_repo_class_meta, mock_repo_class, tmp_path
):
    # Arrange
    mock_repo_class_meta.return_value.heads = [
        MagicMock(name="main"),
    ]
    mock_repo_instance = mock_repo_class.return_value
    directory = tmp_path / "test"
    directory.mkdir()

    # Act
    git_agent = LocalGitAgent(str(directory))
    git_agent.clone_repository()

    # Assert
    assert git_agent.repo == mock_repo_instance
    mock_clone_chosen_branch.assert_not_called()
    mock_clone_default_branch.assert_not_called()


def test_local_git_agent_with_not_existing_directory():
    dirname = "does_not_exist"
    with pytest.raises(ValueError, match=f"{dirname} does not exist."):
        LocalGitAgent(dirname)


def test_local_git_agent_with_empty_directory(tmp_path):
    directory = tmp_path / "empty"
    directory.mkdir()

    with pytest.raises(InvalidGitRepositoryError):
        LocalGitAgent(str(directory))


def test_local_git_agent_with_directory_without_git(tmp_path):
    directory = tmp_path / "not_a_repo"
    directory.mkdir()
    (directory / "some_file.txt").write_text("content")

    with pytest.raises(InvalidGitRepositoryError):
        LocalGitAgent(str(directory))


@pytest.fixture
def repo_with_dated_commits(tmp_path):
    """Build a local repository with one commit per year and return it with its commits."""
    repo_path = tmp_path / "dated_repo"
    repo_path.mkdir()
    repo = Repo.init(path=str(repo_path), initial_branch="main")
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@example.com").release()

    commits = {}
    for year in (2020, 2022, 2024):
        file_path = repo_path / "file.txt"
        file_path.write_text(f"content of {year}")
        repo.index.add([str(file_path)])
        commit_date = datetime(year, 6, 15, 12, 0, tzinfo=timezone.utc)
        commits[year] = repo.index.commit(f"commit of {year}", author_date=commit_date, commit_date=commit_date)

    return repo_path, repo, commits


@pytest.mark.parametrize(
    "based_on_date, expected_year",
    [
        ("2022-06-14", 2022),  # the closest commit was made the next day
        ("2021-01-01", 2020),  # the closest commit was made before the date
        ("2019-01-01", 2020),  # the date is older than the repository itself
        ("2030-01-01", 2024),  # the date is newer than the last commit
    ],
)
def test_git_agent_find_closest_commit(git_agent_base_setup, repo_with_dated_commits, based_on_date, expected_year):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    repo_path, repo, commits = repo_with_dated_commits
    agent.repo = repo
    agent.based_on_date = parse_date_argument(based_on_date)

    # Act
    closest_commit = agent._find_closest_commit()

    # Assert
    assert closest_commit == commits[expected_year].hexsha


def test_git_agent_checkout_version_by_date(git_agent_base_setup, repo_with_dated_commits):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    repo_path, repo, commits = repo_with_dated_commits
    agent.repo = repo
    agent.based_on_date = parse_date_argument("2022-08-01")

    # Act
    agent._checkout_version_by_date()

    # Assert
    assert repo.head.commit == commits[2022]
    assert (repo_path / "file.txt").read_text() == "content of 2022"


def test_git_agent_checkout_version_by_date_without_date(git_agent_base_setup, repo_with_dated_commits):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    repo_path, repo, commits = repo_with_dated_commits
    agent.repo = repo

    # Act
    agent._checkout_version_by_date()

    # Assert
    assert agent.based_on_date is None
    assert repo.head.commit == commits[2024]


def test_git_agent_clone_repository_with_based_on_date_uses_default_branch(git_agent_base_setup):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    agent.based_on_date = parse_date_argument("2022-08-01")

    # Act
    with (
        patch.object(agent, "_check_branch_existence", return_value=True) as mock_check_branch,
        patch.object(agent, "_clone_chosen_branch") as mock_clone_chosen_branch,
        patch.object(agent, "_clone_default_branch") as mock_clone_default_branch,
        patch.object(agent, "_checkout_version_by_date") as mock_checkout_version_by_date,
    ):
        agent.clone_repository()

    # Assert
    mock_clone_default_branch.assert_called_once()
    mock_clone_chosen_branch.assert_not_called()
    mock_check_branch.assert_not_called()
    mock_checkout_version_by_date.assert_called_once()


def test_git_agent_initialization_with_based_on_date(mock_repository_metadata, repo_info, monkeypatch):
    # Arrange
    _, _, _, repo_url = repo_info
    monkeypatch.setenv("GIT_TOKEN", "fake-token-based-on-date")

    # Act
    with patch.object(GitHubMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitHubAgent(repo_url, based_on_date="17.05.2023")

    # Assert
    assert agent.based_on_date == datetime(2023, 5, 17, tzinfo=timezone.utc)


def test_git_agent_initialization_with_invalid_based_on_date(mock_repository_metadata, repo_info, monkeypatch):
    # Arrange
    _, _, _, repo_url = repo_info
    monkeypatch.setenv("GIT_TOKEN", "fake-token-based-on-date")

    # Act & Assert
    with patch.object(GitHubMetadataLoader, "load_data", return_value=mock_repository_metadata):
        with pytest.raises(ValueError, match="Cannot parse date"):
            GitHubAgent(repo_url, based_on_date="the day before yesterday")


def test_git_agent_find_closest_commit_after_detached_head(git_agent_base_setup, repo_with_dated_commits):
    """A previous dated run leaves HEAD detached, later dates still have to see the newer commits."""
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    repo_path, repo, commits = repo_with_dated_commits
    agent.repo = repo
    agent.base_branch = "main"

    agent.based_on_date = parse_date_argument("2020-06-15")
    agent._checkout_version_by_date()
    assert repo.head.is_detached

    # Act
    agent.based_on_date = parse_date_argument("2024-06-15")
    closest_commit = agent._find_closest_commit()

    # Assert
    assert closest_commit == commits[2024].hexsha


def test_git_agent_resolve_history_ref_fetches_configured_branch(git_agent_base_setup):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    agent.repo = MagicMock()
    agent.repo.remotes = [SimpleNamespace(name="origin")]
    agent.based_on_date = parse_date_argument("2022-08-01")

    # Act
    history_ref = agent._resolve_history_ref()

    # Assert
    agent.repo.git.fetch.assert_called_once_with("origin", agent.base_branch)
    assert history_ref == "FETCH_HEAD"


def test_git_agent_resolve_history_ref_falls_back_when_fetch_fails(git_agent_base_setup):
    # Arrange
    agent, _, _, _ = git_agent_base_setup
    agent.repo = MagicMock()
    agent.repo.remotes = [SimpleNamespace(name="origin")]
    agent.repo.git.fetch.side_effect = GitCommandError("fetch", 1)

    def rev_parse(ref):
        if ref != f"origin/{agent.base_branch}":
            raise ValueError(f"unknown revision: {ref}")
        return ref

    agent.repo.rev_parse.side_effect = rev_parse
    agent.based_on_date = parse_date_argument("2022-08-01")

    # Act
    history_ref = agent._resolve_history_ref()

    # Assert
    assert history_ref == f"origin/{agent.base_branch}"


def test_git_agent_checkout_version_by_date_keeps_dirty_local_repository(repo_with_dated_commits):
    # Arrange
    repo_path, repo, commits = repo_with_dated_commits
    agent = LocalGitAgent(str(repo_path), based_on_date="2020-06-15")
    agent.repo = repo
    (repo_path / "file.txt").write_text("work in progress")

    # Act & Assert
    with pytest.raises(ValueError, match="uncommitted changes"):
        agent._checkout_version_by_date()

    assert repo.head.commit == commits[2024]
    assert (repo_path / "file.txt").read_text() == "work in progress"
