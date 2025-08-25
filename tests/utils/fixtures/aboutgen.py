from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_readme_content_aboutgen():
    with patch("osa_tool.aboutgen.about_generator.extract_readme_content", return_value="Sample README") as mock:
        yield mock


@pytest.fixture
def mock_model_handler_aboutgen():
    with patch("osa_tool.aboutgen.about_generator.ModelHandlerFactory.build") as mock_build:
        handler = MagicMock()
        handler.send_request.return_value = "Mocked model output"
        mock_build.return_value = handler
        yield handler
