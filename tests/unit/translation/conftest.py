import os
from unittest.mock import MagicMock

import pytest

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandlerFactory
from osa_tool.translation.dir_translator import DirectoryTranslator


@pytest.fixture
def mock_walk_data():
    return [
        (os.path.normpath("/repo"), [], ["file.py", "data.txt"]),
        (os.path.normpath("/repo"), ["subdir"], ["subdir/module.py", "readme.md"]),
        (os.path.normpath("/repo"), ["subdir2"], []),
    ]


@pytest.fixture
def translator():
    mock_config_loader = MagicMock(spec=ConfigLoader)
    mock_config_loader.config = MagicMock()
    mock_config_loader.config.git.repository = "https://github.com/example/repo"
    mock_config_loader.config.llm.api = "itmo"

    translator = DirectoryTranslator(mock_config_loader)
    translator.model_handler = MagicMock(spec=ModelHandlerFactory.build(mock_config_loader.config))
    return translator
