from unittest.mock import MagicMock, patch

import pytest
from git import Repo

from osa_tool.git_agent.git_agent import GitAgent


@pytest.fixture
def github_agent(mock_load_metadata):
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
    with patch("osa_tool.git_agent.git_agent.load_data_metadata") as mock:
        metadata_mock = MagicMock()
        metadata_mock.default_branch = "main"
        mock.return_value = metadata_mock
        yield mock
