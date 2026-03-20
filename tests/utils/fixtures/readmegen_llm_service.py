from unittest.mock import MagicMock, Mock

import pytest

from osa_tool.operations.docs.readme_generation.models.llm_service import LLMClient
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture
def mock_model_handler():
    """
    Factory fixture to create a mocked ModelHandler with custom side effects.
    
    This fixture returns a factory function that generates a MagicMock instance of a ModelHandler.
    It is primarily used in testing to replace the real ModelHandler with a mock that can simulate
    specific behaviors, such as raising exceptions or returning predetermined responses, without
    requiring actual model inference. This allows isolated unit testing of components that depend
    on the ModelHandler.
    
    Args:
        side_effect: An optional callable, iterable, or exception to set as the side_effect
            for the mock's `send_and_parse` method. If provided, this side_effect will be
            invoked when `send_and_parse` is called, enabling simulation of various
            behaviors (e.g., returning specific values, raising errors). If None, the
            mock's `send_and_parse` method will have no side effect.
    
    Returns:
        A callable factory function that, when called with an optional `side_effect`,
        returns a MagicMock instance configured as a ModelHandler mock.
    """

    def _factory(side_effect=None):
        handler = MagicMock()
        if side_effect is not None:
            handler.send_and_parse.side_effect = side_effect
        return handler

    return _factory


@pytest.fixture
def mock_file_contexts():
    """
    Returns a factory function that creates mock FileContext-like objects for testing.
    This is useful for simulating file objects without actual file I/O operations.
    
    Args:
        None: The outer function takes no parameters.
    
    Returns:
        A factory function `_make_mock` that accepts:
            name: The display name of the file.
            path: The file system path of the file.
            content: The textual content of the file.
        The factory returns a Mock object with `name`, `path`, and `content` attributes set accordingly.
    
    Usage:
        factory = mock_file_contexts()
        mock_file = factory("main.py", "src/main.py", "print('hello')")
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
    Returns a factory function that creates a mocked FileProcessor instance.
    The factory configures the mock to return a predefined list of file contexts when its `process_files` method is called.
    
    This utility is designed for testing components that depend on a FileProcessor, allowing tests to simulate specific file‑processing outcomes without actual file I/O.
    
    Args:
        mock_file_contexts: A callable (typically a mock) that will be invoked to generate each file context. It should accept parameters for file name, path, and content, and return a corresponding mock file‑context object.
    
    Returns:
        A factory function that, when called with a list of file specifications, returns a mocked FileProcessor. The mock’s `process_files` method will return a list of file contexts produced by applying `mock_file_contexts` to each specification.
    
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
def llm_client(mock_config_manager, sourcerank_with_repo_tree, mock_repository_metadata, mock_model_handler):
    """
    Creates and configures an LLMClient instance with mocked dependencies for testing.
    
    This method constructs an LLMClient object using provided mock fixtures and
    configures it with a mock repository tree, SourceRank instance, and model handler.
    It is primarily used in test setups to create a fully configured client with
    controlled dependencies, enabling isolated unit testing of components that depend
    on the LLMClient without requiring real external services or repository access.
    
    Args:
        mock_config_manager: Mock configuration manager for the client.
        sourcerank_with_repo_tree: Factory fixture that creates SourceRank instances
            with a given repository tree structure.
        mock_repository_metadata: Mock repository metadata for the client.
        mock_model_handler: Factory fixture that creates mocked ModelHandler instances.
    
    Returns:
        LLMClient: A configured LLMClient instance with mocked dependencies.
    
    Why:
        This method centralizes the test setup for an LLMClient, ensuring consistent
        configuration across tests. It uses a predefined "FULL" mock repository tree
        to provide a complete example structure, attaches a mocked SourceRank instance
        built from that tree, and injects a mocked ModelHandler. This allows tests to
        focus on specific behaviors without dealing with real repository data or model
        inference, thereby improving test isolation and reliability.
    """
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    client = LLMClient(mock_config_manager, mock_repository_metadata)
    client.model_handler = mock_model_handler()
    client.sourcerank = sourcerank
    client.tree = sourcerank.tree
    return client
