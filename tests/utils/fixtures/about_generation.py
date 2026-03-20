from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_readme_content_aboutgen():
    """
    Mocks the extraction of README content during the about generation process.
    
    This method uses a patch to intercept the `extract_readme_content` function, ensuring it returns a predefined sample string instead of performing actual file operations. It is designed to be used as a context manager or fixture in a testing environment, allowing tests to run without dependencies on actual README files.
    
    Args:
        None.
    
    Yields:
        unittest.mock.MagicMock: The mock object for the extract_readme_content function, which will return "Sample README" when called.
    
    Why:
        This mocking is used to isolate the about generation logic from file system operations, ensuring tests are fast, reliable, and not affected by missing or varying README file content.
    """
    with patch(
        "osa_tool.operations.docs.about_generation.about_generator.extract_readme_content", return_value="Sample README"
    ) as mock:
        yield mock


@pytest.fixture
def mock_model_handler_aboutgen():
    """
    Mocks the ModelHandler for about generation using a context manager.
    
    This method patches the ModelHandlerFactory to return a mocked handler that simulates
    a model response. It is designed to be used in tests to avoid making actual API calls.
    The mocking is necessary because about generation typically requires external API calls,
    and using a mock allows tests to run quickly, reliably, and without network dependencies.
    
    Yields:
        MagicMock: A mocked model handler instance. The handler's `send_request` method
        is preconfigured to return the string "Mocked model output" when called.
    """
    with patch("osa_tool.operations.docs.about_generation.about_generator.ModelHandlerFactory.build") as mock_build:
        handler = MagicMock()
        handler.send_request.return_value = "Mocked model output"
        mock_build.return_value = handler
        yield handler
