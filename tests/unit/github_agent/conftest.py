import pytest
from unittest.mock import MagicMock
from git import Repo
from osa_tool.github_agent.github_agent import GithubAgent

@pytest.fixture
def github_agent():
    agent = GithubAgent(repo_url="https://github.com/testuser/testrepo")
    agent.repo = MagicMock(Repo)
    agent.token = "test_token"
    agent.base_branch = "main"
    agent.repo.head.commit.message = "Initial commit"
    agent.fork_url = "https://github.com/testuser/testrepo-fork"
    agent.branch_name = "feature-branch"
    return agent
