import os
import tempfile
from unittest.mock import Mock, patch, ANY

import pytest
from git import Repo, GitCommandError

from osa_tool.core.git.git_agent import GitHubAgent, GitverseAgent, GitLabAgent
from osa_tool.core.git.metadata import (
    GitHubMetadataLoader,
    GitverseMetadataLoader,
    GitLabMetadataLoader,
)
from osa_tool.utils.utils import parse_folder_name


@pytest.fixture
def temp_clone_dir():
    """
    Creates a temporary directory that is automatically cleaned up after use.
    
    This method utilizes a context manager to provide a temporary directory path. It is designed to be used as a generator or context manager, ensuring that the directory and its contents are deleted once the execution leaves the context. This is useful for safely creating a temporary workspace, such as for cloning a repository or staging files, without leaving residual data.
    
    Yields:
        str: The path to the newly created temporary directory.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


@pytest.fixture
def mock_repo():
    """
    Creates a mock object representing a git repository.
    
    This method initializes a mock object with the specification of a Repo class and attaches a mock git attribute to it. The mock is used for testing purposes to simulate a git repository without requiring an actual repository or git operations, allowing isolated unit tests.
    
    Returns:
        Mock: A mock repository object with a mocked git attribute.
    """
    repo = Mock(spec=Repo)
    repo.git = Mock()
    return repo


@pytest.fixture
def git_agent_base_setup(temp_clone_dir, mock_repository_metadata, repo_info, monkeypatch):
    """
    Sets up a base GitHubAgent for testing by mocking dependencies and environment.
    
    This method creates a GitHubAgent instance for a given repository, using mocked
    repository metadata and a temporary directory for cloning. It also sets a fake
    Git token in the environment to simulate authentication. The method yields the
    agent and related context information for use in test fixtures.
    
    Args:
        temp_clone_dir: A temporary directory path where the repository clone will be simulated.
        mock_repository_metadata: Mocked repository metadata to be returned by the loader.
        repo_info: A tuple containing platform, owner, repository name, and repository URL.
        monkeypatch: Pytest monkeypatch fixture for modifying environment and attributes.
    
    Yields:
        A tuple containing:
            - The configured GitHubAgent instance.
            - The platform string from repo_info.
            - The repository URL.
            - The temporary clone directory path.
    
    Why:
        The GitHubAgent normally requires a real Git token and repository metadata.
        This setup mocks these dependencies to allow isolated testing without
        external API calls or actual cloning. The temporary directory simulates a
        clone location, and the mocked loader prevents real data fetching.
    """
    platform, owner, repo_name, repo_url = repo_info

    monkeypatch.setenv("GIT_TOKEN", "fake-token-base-setup")

    with patch.object(GitHubMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitHubAgent(repo_url)

        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent, platform, repo_url, temp_clone_dir


def test_git_agent_initialization(git_agent_base_setup):
    """
    Verifies that the Git agent is correctly initialized with the expected properties.
    
    This test method checks if the agent's repository URL, authentication token,
    base branch, working branch name, and clone directory are properly set
    up based on the provided fixture. The assertions ensure the agent's state
    matches the fixture-provided values and expected defaults.
    
    Args:
        git_agent_base_setup: A fixture providing a tuple containing the initialized
            agent, the platform instance, the repository URL, and the temporary
            directory path.
    
    Why:
    - The token is verified against a hardcoded fake value ("fake-token-base-setup") because the test uses a mocked authentication token to avoid real credentials.
    - The base branch is compared to the agent's metadata default branch to confirm the agent correctly references the repository's default branch.
    - The working branch name is checked for a fixed value ("osa_tool") as this is the expected branch name used by the OSA Tool for its operations.
    - The clone directory path is validated to start with the temporary directory path to ensure the agent clones into the correct, isolated test location.
    """
    # Arrange
    agent, platform, repo_url, temp_dir = git_agent_base_setup

    # Act / Assert
    assert agent.repo_url == repo_url
    assert agent.token == "fake-token-base-setup"
    assert agent.base_branch == agent.metadata.default_branch
    assert agent.branch_name == "osa_tool"
    assert agent.clone_dir.startswith(temp_dir)


def test_git_agent_clone_repository_success_new(git_agent_base_setup, mock_repo):
    """
    Verifies that the git agent successfully clones a repository by falling back to an authenticated URL after an unauthenticated clone attempt fails.
    
    The test mocks the cloning process to simulate a failure on the first attempt (unauthenticated) and a success on the second attempt (authenticated), ensuring the agent correctly updates its internal repository state.
    
    WHY: This test validates the fallback mechanism in the agent's cloning strategy, which is designed to first try an unauthenticated clone (which may fail due to permissions or rate limits) and then retry with an authenticated URL, ensuring robust repository acquisition.
    
    Args:
        git_agent_base_setup: A fixture providing the base setup for the git agent, including the agent instance, platform, repository URL, and temporary directory.
        mock_repo: A mock object representing the successfully cloned git repository.
    
    Behavior:
        - Mocks the authenticated and unauthenticated URLs returned by the agent's internal methods.
        - Mocks `git.Repo.clone_from` to raise an exception on the first call (unauthenticated) and return the mock repository on the second call (authenticated).
        - Ensures the agent calls `clone_from` twice with the correct URLs in order.
        - Verifies the agent's internal repository state is updated to the mock repository after successful cloning.
    """
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
    """
    Verifies that the GitAgent correctly handles a scenario where the repository directory already exists and is a valid Git repository.
    
    The test ensures that when `clone_repository` is called on an existing local repository, the agent successfully initializes its internal repository object and associates it with the correct working directory without re-cloning. This validates that the agent's cloning logic correctly identifies and reuses an existing valid Git repository, preventing unnecessary network operations.
    
    Args:
        git_agent_base_setup: A fixture providing the GitAgent instance, platform, repository URL, and temporary directory.
        temp_clone_dir: A fixture providing the path for the temporary clone directory.
    
    Steps performed by the test:
    1. Creates a temporary directory and initializes a valid Git repository with user configuration.
    2. Calls `agent.clone_repository()`.
    3. Asserts that the agent's internal `repo` attribute is a valid `Repo` object and that its working directory matches the expected clone path.
    """
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
    """
    Verifies that the GitAgent correctly handles and re-raises a GitCommandError during the repository cloning process.
    
    This test simulates a failure in the underlying Git command (e.g., repository not found) by patching the cloning mechanism to raise a GitCommandError. It ensures that the agent catches the error and raises a generic Exception with a descriptive error message formatted by the internal error handler.
    
    WHY: The test validates that cloning failures are properly caught and re-raised as user-friendly exceptions, ensuring robust error handling in the cloning workflow.
    
    Args:
        git_agent_base_setup: A fixture providing the GitAgent instance, platform mock, repository URL, and temporary directory path.
    
    Raises:
        Exception: When the agent's clone_repository method is called and a GitCommandError is simulated, the test expects a generic Exception to be raised with a message matching the pattern "Git operation 'cloning repository.*' failed".
    """
    # Arrange
    agent, platform, repo_url, temp_dir = git_agent_base_setup

    # Act / Assert
    git_error = GitCommandError("clone", 128, b"fatal: repository not found")
    with patch("git.Repo.clone_from", side_effect=git_error):
        # Match changed: now we catch the message from _handle_git_error
        with pytest.raises(Exception, match=r"Git operation 'cloning repository.*' failed"):
            agent.clone_repository()


def test_git_agent_create_and_checkout_branch_new(git_agent_base_setup, mock_repo):
    """
    Tests that the git agent correctly creates and checks out a new branch when it does not already exist.
    
    WHY: The test verifies that the agent's `create_and_checkout_branch` method triggers the appropriate Git command (`checkout -b`) when the target branch is not present in the repository's list of existing branches.
    
    Args:
        git_agent_base_setup: A fixture providing the base setup for the GitAgent, including the agent instance and its dependencies.
        mock_repo: A mocked git repository object used to simulate repository state and track git commands.
    """
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
    """
    Tests that the Git agent correctly checks out a branch when it already exists.
    
    This test verifies that if the target branch is already present in the repository's heads, the agent skips the creation step and performs a checkout of the existing branch. This ensures the agent's branch handling is efficient and avoids redundant operations.
    
    Args:
        git_agent_base_setup: A fixture providing the base setup for the Git agent, including the agent instance and its dependencies.
        mock_repo: A mock object representing the git repository, used to simulate the repository state and verify interactions.
    """
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
    """
    Verifies that the GitAgent successfully commits and pushes changes to a remote repository.
    
    This test ensures that the agent correctly stages all files, creates a commit with the provided message, updates the remote URL with authentication credentials, and performs a push with the expected flags (force_with_lease). The test mocks the repository interactions to isolate and verify the agent's behavior without actual Git operations.
    
    Args:
        git_agent_base_setup: A fixture providing the base setup for the GitAgent, including the agent instance and related mocks.
        mock_repo: A mock object representing the git repository, used to verify calls to Git commands.
    
    Returns:
        None.
    """
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
    """
    Verifies that the commit_and_push_changes method returns False and does not attempt to push when there are no changes to commit. This test simulates a clean working tree scenario where a GitCommandError is raised during the commit step.
    
    Args:
        git_agent_base_setup: A fixture providing the base setup for the Git agent, including the agent instance and related configurations.
        mock_repo: A mocked git.Repo object used to simulate Git command behaviors and track calls.
    
    Returns:
        bool: Always returns False in this test case as it asserts the result of a failed commit due to a clean working tree. The test ensures the method correctly handles the error by returning False and not proceeding to push.
    """
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
    """
    Tests the `upload_report` method of the GitAgent to ensure it correctly handles report uploads to a specific branch.
    
    This test verifies the end-to-end process of uploading a report, including checking out the target branch, moving the file to the clone directory, committing changes, and pushing to the remote repository. It also validates that the report URL is correctly appended to the agent's pull request report body.
    
    Args:
        git_agent_base_setup: A fixture providing the base setup for the GitAgent, including the agent instance and related mocks.
        mock_repo: A mock object representing the git repository.
        temp_clone_dir: A temporary directory path used for simulating the local clone environment.
    
    Why:
        This test ensures the upload workflow functions correctly in isolation by mocking the git operations and verifying the sequence of calls and state changes. It confirms that the report is properly staged, committed, and pushed to a dedicated branch, and that the resulting URL is integrated into the pull request documentation.
    """
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
    """
    Creates a GitHubAgent instance for testing with mocked dependencies.
    
    This fixture is used to isolate tests from external dependencies by mocking the metadata loader and environment variables. It ensures the GitHubAgent operates in a controlled, repeatable test environment.
    
    Args:
        temp_clone_dir: Temporary directory path for cloning repositories.
        mock_repository_metadata: Mocked repository metadata to be returned by the loader.
        repo_info: Tuple containing platform, owner, repository name, and repository URL.
        monkeypatch: Pytest monkeypatch fixture for modifying environment.
    
    Yields:
        GitHubAgent: A configured GitHubAgent instance ready for testing.
    
    Why:
    - The GIT_TOKEN environment variable is set to a fixture value to avoid using real credentials in tests.
    - The GitHubMetadataLoader.load_data method is patched to return the provided mock data, preventing actual API calls.
    - The agent's clone directory is explicitly set to a subdirectory within the temporary path to ensure isolated test runs.
    """
    platform, owner, repo_name, repo_url = repo_info
    monkeypatch.setenv("GIT_TOKEN", "fixture-token-github")
    with patch.object(GitHubMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitHubAgent(repo_url)
        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent


def test_github_agent_load_metadata(github_agent_instance, mock_repository_metadata):
    """
    Verifies that the GitHub agent correctly loads and stores repository metadata upon initialization.
    
    This test ensures that the agent's metadata attribute is properly set after initialization, confirming that the agent is ready for subsequent operations that depend on this metadata.
    
    Args:
        github_agent_instance: The instance of the GitHub agent being tested.
        mock_repository_metadata: The expected metadata object used for verification.
    """
    # Arrange / Act / Assert
    assert github_agent_instance.metadata == mock_repository_metadata


def test_github_agent_create_fork_success(github_agent_instance, mock_requests_response_factory, repo_info):
    """
    Tests the successful creation of a fork by the GitHub agent.
    
    This test verifies that the `create_fork` method correctly constructs the API request,
    includes proper authorization, and updates the agent's state with the resulting fork URL.
    
    Args:
        github_agent_instance: An instance of the GitHub agent class under test.
        mock_requests_response_factory: A fixture providing a mock response factory for HTTP requests.
        repo_info: A tuple containing platform, owner, repository name, and repository URL information.
    
    Why this test is structured this way: It mocks the environment variable for the GitHub token and the HTTP POST request to isolate the test from external API dependencies, ensuring it only validates the agent's internal logic and state updates.
    
    Attributes Initialized:
        fork_url: The URL of the created fork on GitHub, stored on the agent instance.
    """
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
    """
    Tests the failure scenario for creating a GitHub fork via the agent.
    
    This test verifies that the `create_fork` method raises a `ValueError` with a specific message when the underlying API request fails with a 401 status code (unauthorized). It uses mocking to simulate the failed API response.
    
    Why this test is needed: It ensures the agent correctly handles authentication failures (e.g., invalid or missing tokens) by raising a descriptive error, preventing silent failures in the fork creation workflow.
    
    Args:
        github_agent_instance: An instance of the agent class to test.
        mock_requests_response_factory: A fixture providing a factory to create mock HTTP responses.
    
    Raises:
        AssertionError: If the expected `ValueError` is not raised.
    """
    # Arrange
    mock_response = mock_requests_response_factory(status_code=401, text_data="Bad credentials")

    # Act / Assert
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token_for_env"}):
        with patch("requests.post", return_value=mock_response):
            with pytest.raises(ValueError, match=r"API operation 'creating GitHub fork' failed with status 401"):
                github_agent_instance.create_fork()


def test_github_agent_star_repository_already_starred(github_agent_instance, mock_requests_response_factory, repo_info):
    """
    Tests the scenario where the repository is already starred when calling star_repository.
    
    This test verifies that when the repository is already starred by the authenticated user,
    the star_repository method performs a GET request to check the status and does NOT
    perform a subsequent PUT request to star it again. This ensures the method avoids redundant API calls.
    
    Args:
        github_agent_instance: An instance of the agent class containing the method under test.
        mock_requests_response_factory: A fixture providing a factory to create mock HTTP responses.
        repo_info: A tuple containing platform, owner, repository name, and repository URL
                   used to construct the expected API endpoint.
    
    Why:
        The test validates that the method correctly handles the case where a repository is already starred,
        preventing unnecessary PUT requests and ensuring efficient API usage. It mocks a 204 response from the GET request,
        which indicates the repository is already starred, and confirms no PUT request is made.
    """
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
    """
    Tests the successful star repository operation of the GitHub agent.
    
    This test verifies that the `star_repository` method correctly sends a GET request to check if a repository is already starred, followed by a PUT request to star it, when the repository is not already starred. It mocks the HTTP responses and the environment variable for the token.
    
    The test simulates a scenario where the repository is not starred (the initial GET returns a 404 status), ensuring the agent proceeds to star it via a PUT request. This validates the agent's ability to handle the expected API flow without actual network calls.
    
    Args:
        github_agent_instance: An instance of the agent class being tested.
        mock_requests_response_factory: A fixture providing a factory to create mock HTTP response objects.
        repo_info: A tuple containing platform, owner, repository name, and repository URL used to construct the expected API endpoint.
    
    Returns:
        None
    """
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


def test_github_agent_star_repository_failure_non_critical(
    github_agent_instance, mock_requests_response_factory, repo_info
):
    """
    Tests that the star_repository method handles a non-critical failure (403 Forbidden) gracefully.
    
    This test verifies that when the Gitverse API returns a 403 Forbidden response during the initial GET request to check star status, the star_repository method does not raise an exception and execution continues. This is because a 403 is treated as a non-critical failure—it indicates the user lacks permission to check the star status, but the method should not halt the overall process. The test mocks the external HTTP request to simulate this specific failure scenario.
    
    Args:
        github_agent_instance: An instance of the GitverseAgent class, configured for testing.
        mock_requests_response_factory: A fixture providing a factory to create mock HTTP responses for requests.get.
        repo_info: Fixture or data containing repository information (e.g., URL) used in the test context.
    """
    # Arrange
    # 403 - does not fail the execution
    mock_response_check = mock_requests_response_factory(status_code=403, text_data="Forbidden")

    # Act
    with patch.dict(os.environ, {"GIT_TOKEN": "any_token_for_env"}):
        with patch("requests.get", return_value=mock_response_check) as mock_get:
            github_agent_instance.star_repository()
            # Assert
            mock_get.assert_called_once()


@pytest.fixture
def gitlab_agent_instance(temp_clone_dir, mock_repository_metadata, repo_info, monkeypatch):
    """
    Creates a GitLabAgent instance for testing with mocked environment and metadata.
    This fixture is used to isolate tests from real GitLab API calls and external dependencies by providing a pre‑configured agent with mocked metadata and a controlled clone directory.
    
    Args:
        temp_clone_dir: Temporary directory path for cloning the repository.
        mock_repository_metadata: Mocked repository metadata to be returned by the loader.
        repo_info: Tuple containing platform, owner, repository name, and repository URL.
        monkeypatch: Pytest monkeypatch fixture for modifying environment variables.
    
    Yields:
        GitLabAgent: Configured GitLabAgent instance ready for testing. The instance has its clone directory set to a subdirectory of `temp_clone_dir` derived from the repository URL, and the GitLabMetadataLoader.load_data method is patched to return the provided mock metadata. The GITLAB_TOKEN environment variable is also set to a dummy value to satisfy authentication requirements during testing.
    """
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
    """
    Tests the successful creation of a fork by the GitLab agent.
    
    This test verifies that the GitLab agent correctly creates a fork of a repository,
    including the necessary API calls and the setting of the resulting fork URL.
    The test mocks the GitLab API to simulate a successful fork creation, ensuring the agent
    makes the expected HTTP requests and properly stores the fork URL.
    
    Args:
        gitlab_agent_instance: The GitLab agent instance under test.
        mock_requests_response_factory: Fixture providing a factory for mock HTTP responses.
        mock_repository_metadata: Mocked repository metadata.
        repo_info: Tuple containing platform, owner, repository name, and repository URL.
        mock_config_manager: Mocked configuration manager, configured for GitLab.
    
    Why this test is structured as it is: It uses mocking to isolate the agent from the actual GitLab API,
    allowing validation of the agent's internal logic and HTTP interactions without external dependencies.
    The test checks that the agent constructs the correct API endpoint, uses proper authentication,
    and handles the API response by setting the fork_url attribute.
    
    Returns:
        None. This is a test method.
    """
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
    """
    Creates a GitverseAgent instance for testing with mocked dependencies.
    
    This fixture is used to isolate tests by providing a GitverseAgent with a controlled environment. It sets a dummy authentication token and mocks the metadata loading process to avoid external API calls during testing.
    
    Args:
        temp_clone_dir: The temporary directory path where the repository will be cloned.
        mock_repository_metadata: The mocked repository metadata to be returned by the loader.
        repo_info: A tuple containing platform, owner, repository name, and repository URL.
        monkeypatch: The pytest monkeypatch fixture for modifying environment variables.
    
    Yields:
        GitverseAgent: The configured GitverseAgent instance ready for testing. The agent's clone directory is set to a subdirectory within temp_clone_dir based on the repository URL.
    """
    platform, owner, repo_name, repo_url = repo_info
    monkeypatch.setenv("GITVERSE_TOKEN", "fixture-token-gitverse")
    with patch.object(GitverseMetadataLoader, "load_data", return_value=mock_repository_metadata):
        agent = GitverseAgent(repo_url)
        agent.clone_dir = os.path.join(temp_clone_dir, parse_folder_name(repo_url))
        yield agent


def test_gitverse_agent_create_fork_success(gitverse_agent_instance, mock_requests_response_factory, repo_info):
    """
    Tests the successful creation of a fork by the GitverseAgent.
    
    This test verifies that the create_fork method correctly creates a fork when the user is not the repository owner and no existing fork is found. It mocks the API requests to simulate a successful fork creation scenario.
    
    Why this test is structured this way: The test simulates a specific success path where the authenticated user is different from the repository owner and no prior fork exists, ensuring the method performs the expected API calls and correctly updates the fork_url.
    
    Args:
        gitverse_agent_instance: An instance of GitverseAgent to test.
        mock_requests_response_factory: Fixture providing a mock response factory for requests.
        repo_info: Tuple containing platform, owner, repository name, and repository URL.
    
    Returns:
        None
    """
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
    """
    Tests the successful scenario of GitverseAgent.star_repository.
    
    This test verifies that the star_repository method correctly stars a repository when the repository is not already starred. It mocks the underlying HTTP requests to simulate a successful API call.
    
    The test simulates a scenario where the initial GET request to check star status returns a 404 (indicating the repository is not starred), and the subsequent PUT request to star the repository returns a 204 (success). This ensures the method proceeds through the full star operation without errors.
    
    Args:
        gitverse_agent_instance: An instance of GitverseAgent to test.
        mock_requests_response_factory: A fixture providing a mock response factory for HTTP requests.
        repo_info: Contains information about the repository being tested.
    
    Returns:
        None.
    """
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
    """
    Tests the scenario where the repository is already starred.
    
    This test verifies that when the repository is already starred by the user,
    the star_repository method checks the status and does not attempt to star it again.
    It ensures the method performs only a GET request to confirm the starred status and does not make a redundant PUT request.
    
    Args:
        gitverse_agent_instance: An instance of the GitverseAgent to test.
        mock_requests_response_factory: A fixture providing a mock response factory for requests.
        repo_info: Provides repository information for the test context.
    """
    # Arrange
    mock_response_check = mock_requests_response_factory(status_code=204)

    with patch.dict(os.environ, {"GITVERSE_TOKEN": "any_token_for_env"}):
        with patch("requests.get", return_value=mock_response_check) as mock_get, patch("requests.put") as mock_put:
            # Act
            gitverse_agent_instance.star_repository()

            # Assert
            mock_get.assert_called_once()
            mock_put.assert_not_called()
