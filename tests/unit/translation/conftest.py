import os
from unittest.mock import MagicMock

import pytest

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandlerFactory
from osa_tool.translation.dir_translator import DirectoryTranslator


@pytest.fixture
def mock_walk_data():
    """
    Mock data for os.walk.
    
        Returns a list of tuples that mimic the output of `os.walk` for a
        repository structure. Each tuple contains:
          * the normalized root path,
          * a list of subdirectories,
          * a list of files in that root.
    
        The sample data includes a root directory with two files, a subdirectory
        containing a module and a readme, and an empty subdirectory.
    
        Returns:
            list[tuple[str, list[str], list[str]]]: Mocked walk data.
    """
    return [
        (os.path.normpath("/repo"), [], ["file.py", "data.txt"]),
        (os.path.normpath("/repo"), ["subdir"], ["subdir/module.py", "readme.md"]),
        (os.path.normpath("/repo"), ["subdir2"], []),
    ]


@pytest.fixture
def translator():
    """
    Creates a mock DirectoryTranslator instance for testing purposes.
    
    This helper function sets up a mock configuration loader with a sample Git repository URL and LLM API name, then constructs a DirectoryTranslator using that mock loader. It also replaces the translator's `model_handler` attribute with a mocked `ModelHandlerFactory` instance.
    
    Args:
        None
    
    Returns:
        DirectoryTranslator: A DirectoryTranslator instance whose configuration and model handler are mocked for use in tests.
    """
    mock_config_loader = MagicMock(spec=ConfigLoader)
    mock_config_loader.config = MagicMock()
    mock_config_loader.config.git.repository = "https://github.com/example/repo"
    mock_config_loader.config.llm.api = "llama"

    translator = DirectoryTranslator(mock_config_loader)
    translator.model_handler = MagicMock(spec=ModelHandlerFactory.build(mock_config_loader.config))
    return translator
