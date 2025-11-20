from unittest.mock import MagicMock, Mock

import pytest

from osa_tool.readmegen.models.llm_service import LLMClient
from osa_tool.utils.prompts_builder import PromptLoader
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
def mock_file_contexts():
    """
    Returns a factory to create mock FileContext-like objects.
    Usage: mock_file_contexts("main.py", "src/main.py", "print('hello')")
    """

    def _make_mock(name: str, path: str, content: str):
        mock = Mock()
        mock.name = name
        mock.path = path
        mock.content = content
        return mock

    return _make_mock


@pytest.fixture
def mock_file_processor_factory(mock_file_contexts):
    """
    Returns a factory to create a mocked FileProcessor that returns predefined file contexts.
    Usage:
        mock_fp = mock_file_processor_factory([
            ("main.py", "src/main.py", "code1"),
            ("readme.md", "README.md", "docs")
        ])
        with patch("...FileProcessor", return_value=mock_fp): ...
    """

    def _make_processor(file_specs):
        mock_fp = Mock()
        file_contexts = [mock_file_contexts(name, path, content) for name, path, content in file_specs]
        mock_fp.process_files.return_value = file_contexts
        return mock_fp

    return _make_processor


@pytest.fixture
def llm_client(mock_config_loader, sourcerank_with_repo_tree, mock_repository_metadata, mock_model_handler):
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    client = LLMClient(mock_config_loader, PromptLoader(), mock_repository_metadata)
    client.model_handler = mock_model_handler()
    client.sourcerank = sourcerank
    client.tree = sourcerank.tree
    return client
