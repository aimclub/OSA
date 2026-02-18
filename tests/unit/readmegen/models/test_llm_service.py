from unittest.mock import MagicMock, patch

import pytest

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler
from osa_tool.readmegen.models.llm_service import LLMClient


@pytest.fixture
def mock_llm_client():
    """
    Creates a mocked LLMClient instance for testing purposes.
    
        This helper function constructs a mock configuration loader that
        contains a fake Git repository URL. It then patches the
        `ModelHandlerFactory`, `SourceRank`, and `PromptBuilder` classes
        to return predefined mock objects with controlled return values.
        Finally, it returns an `LLMClient` initialized with the mocked
        configuration loader.
    
        Returns:
            LLMClient: An LLMClient instance configured with mocked
            dependencies for unit testing.
    """
    mock_config_loader = MagicMock(spec=ConfigLoader)
    mock_git_config = MagicMock()
    mock_git_config.repository = "https://github.com/example/repo"
    mock_config = MagicMock()
    mock_config.git = mock_git_config
    mock_config_loader.config = mock_config

    with (
        patch("osa_tool.models.models.ModelHandlerFactory.build") as mock_model_handler_factory,
        patch("osa_tool.readmegen.models.llm_service.SourceRank") as mock_source_rank,
        patch("osa_tool.readmegen.models.llm_service.PromptBuilder") as mock_prompt_builder,
    ):
        # ModelHandler
        mock_model_handler = MagicMock(ModelHandler)
        mock_model_handler.send_request.return_value = "mock_response"
        mock_model_handler_factory.return_value = mock_model_handler
        # SourceRank
        mock_source_rank_instance = MagicMock()
        mock_source_rank_instance.tree = "examples/example.py"
        mock_source_rank.return_value = mock_source_rank_instance
        # PromptBuilder
        mock_prompt_builder_instance = MagicMock()
        mock_prompt_builder_instance.get_prompt_core_features.return_value = "mock_prompt_core_features"
        mock_prompt_builder_instance.get_prompt_overview.return_value = "mock_prompt_overview"
        mock_prompt_builder_instance.get_prompt_getting_started.return_value = "mock_prompt_getting_started"
        mock_prompt_builder_instance.get_prompt_preanalysis.return_value = "mock_prompt_preanalysis"
        mock_prompt_builder.return_value = mock_prompt_builder_instance

        return LLMClient(mock_config_loader)


@pytest.fixture
def mock_response_json():
    """
    Return a mock JSON response string.
    
    This method returns a hard‑coded JSON string that represents a mock
    response containing a list of key file paths. The JSON structure
    includes a single key, ``key_files``, whose value is an array of
    file paths.
    
    Returns:
        str: A JSON-formatted string with a ``key_files`` array of file paths.
    """
    return """
    {
        "key_files": [
            "src/main.py",
            "src/api/handlers.py"
        ]
    }
    """


def test_get_responses(mock_llm_client):
    """
    Test that the LLM client returns the expected responses for all sections.
    
    Parameters
    ----------
    mock_llm_client : object
        A mocked LLM client instance whose `run_request` method is replaced with a
        MagicMock that returns a predefined JSON string.
    
    Returns
    -------
    None
        This test function does not return a value; it performs assertions to
        verify that `get_responses` returns the same mock response for each
        section (core_features, overview, getting_started).
    """
    # Arrange
    mock_response = '{"text": "mock_response"}'
    mock_llm_client.run_request = MagicMock(side_effect=lambda prompt: mock_response)
    # Act
    core_features, overview, getting_started = mock_llm_client.get_responses()
    # Assert
    assert core_features == '{"text": "mock_response"}'
    assert overview == '{"text": "mock_response"}'
    assert getting_started == '{"text": "mock_response"}'


def test_get_key_files(mock_llm_client, mock_response_json):
    """
    Test that the LLM client correctly retrieves key files.
    
    Parameters
    ----------
    mock_llm_client
        A mocked LLM client instance whose `run_request` method is patched to return a
        predefined JSON response.
    mock_response_json
        The JSON payload that the mocked `run_request` should return, representing the
        key files.
    
    Returns
    -------
    None
        This test function does not return a value; it asserts that the client returns
        the expected list of key files.
    """
    # Arrange
    mock_llm_client.run_request = MagicMock(return_value=mock_response_json)
    # Act
    key_files = mock_llm_client.get_key_files()
    # Assert
    assert key_files == ["src/main.py", "src/api/handlers.py"]
