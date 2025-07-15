import pytest
from unittest.mock import MagicMock
from git import Repo
from osa_tool.git_agent.git_agent import GitAgent


@pytest.fixture
def github_agent():
    agent = GitAgent(repo_url="https://github.com/testuser/testrepo", repo_branch_name = "main")
    agent.repo = MagicMock(Repo)
    agent.token = "test_token"
    agent.repo.head.commit.message = "Initial commit"
    agent.fork_url = "https://github.com/testuser/testrepo-fork"
    agent.branch_name = "feature-branch"
    return agent
