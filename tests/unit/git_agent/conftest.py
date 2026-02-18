from unittest.mock import MagicMock, patch

import pytest
from git import Repo

from osa_tool.git_agent.git_agent import GitAgent


@pytest.fixture
def github_agent(mock_load_metadata):
    """
    Method Name: github_agent
    
    Creates and configures a GitAgent instance for testing purposes.
    
    Parameters
    ----------
    mock_load_metadata
        Placeholder for a mock object used to load metadata (not used in this function).
    
    Returns
    -------
    GitAgent
        A GitAgent instance with preset attributes for testing, including:
        - repo: a mocked Repo object
        - token: a test token string
        - base_branch: the base branch name
        - repo.head.commit.message: the commit message of the head
        - fork_url: the URL of the forked repository
        - branch_name: the name of the feature branch
    """
    agent = GitAgent(repo_url="https://github.com/testuser/testrepo")
    agent.repo = MagicMock(Repo)
    agent.token = "test_token"
    agent.base_branch = "main"
    agent.repo.head.commit.message = "Initial commit"
    agent.fork_url = "https://github.com/testuser/testrepo-fork"
    agent.branch_name = "feature-branch"
    return agent


@pytest.fixture(autouse=True)
def mock_load_metadata():
    """
    Mock fixture that patches the `load_data_metadata` function used by the git agent.
    
    This fixture automatically replaces the `load_data_metadata` function with a
    `MagicMock` that returns an object having a `default_branch` attribute set to
    ``"main"``.  The patched mock is yielded to the test, allowing tests to
    inspect or modify its behavior.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    MagicMock
        The mocked `load_data_metadata` function, which can be used by tests to
        assert calls or to customize its return value.
    """
    with patch("osa_tool.git_agent.git_agent.load_data_metadata") as mock:
        metadata_mock = MagicMock()
        metadata_mock.default_branch = "main"
        mock.return_value = metadata_mock
        yield mock
