from unittest.mock import patch

import pytest

from osa_tool.readmegen.prompts.prompts_builder import PromptBuilder
from tests.utils.fixtures.analytics_sourcerank import sourcerank_with_repo_tree
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture
def mock_readme_content_prompts():
    with patch(
        "osa_tool.readmegen.prompts.prompts_builder.extract_readme_content", return_value="Sample README"
    ) as mock:
        yield mock


@pytest.fixture
def prompt_builder(mock_config_loader, mock_readme_content_prompts, sourcerank_with_repo_tree, load_metadata_prompts):
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    pb = PromptBuilder(mock_config_loader)
    pb.sourcerank = sourcerank
    pb.tree = sourcerank.tree
    return pb
