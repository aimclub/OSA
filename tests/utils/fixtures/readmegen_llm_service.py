from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_model_handler():
    """Factory fixture to create a mocked ModelHandler with custom side effects."""

    def _factory(side_effect=None):
        handler = MagicMock()
        if side_effect is not None:
            handler.send_and_parse.side_effect = side_effect
        return handler

    return _factory
