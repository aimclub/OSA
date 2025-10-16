from unittest.mock import MagicMock

import pytest

from osa_tool.readmegen.models.llm_service import LLMClient
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture
def mock_model_handler():
    """Factory fixture to create a mocked ModelHandler with custom side effects."""

    def _factory(side_effect=None):
        handler = MagicMock()
        if side_effect is not None:
            handler.send_request.side_effect = side_effect
        return handler

    return _factory


@pytest.fixture
def llm_client(
    mock_config_loader, prompt_builder, sourcerank_with_repo_tree, mock_repository_metadata, mock_model_handler
):
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    client = LLMClient(mock_config_loader, mock_repository_metadata)
    client.model_handler = mock_model_handler()
    client.sourcerank = sourcerank
    client.tree = sourcerank.tree
    return client
