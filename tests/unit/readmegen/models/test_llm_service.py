from unittest.mock import MagicMock, patch

import pytest

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler
from osa_tool.readmegen.models.llm_service import LLMClient


@pytest.fixture
def mock_llm_client():
    mock_config_loader = MagicMock(spec=ConfigLoader)
    mock_git_config = MagicMock()
    mock_git_config.repository = "https://github.com/example/repo"
    mock_config = MagicMock()
    mock_config.git = mock_git_config
    mock_config_loader.config = mock_config

    with (
        patch(
            "osa_tool.models.models.ModelHandlerFactory.build"
        ) as mock_model_handler_factory,
        patch("osa_tool.readmegen.models.llm_service.SourceRank") as mock_source_rank,
        patch(
            "osa_tool.readmegen.models.llm_service.PromptBuilder"
        ) as mock_prompt_builder,
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
        mock_prompt_builder_instance.get_prompt_core_features.return_value = (
            "mock_prompt_core_features"
        )
        mock_prompt_builder_instance.get_prompt_overview.return_value = (
            "mock_prompt_overview"
        )
        mock_prompt_builder_instance.get_prompt_getting_started.return_value = (
            "mock_prompt_getting_started"
        )
        mock_prompt_builder_instance.get_prompt_preanalysis.return_value = (
            "mock_prompt_preanalysis"
        )
        mock_prompt_builder.return_value = mock_prompt_builder_instance

        return LLMClient(mock_config_loader)


def test_get_responses(mock_llm_client):
    # Arrange
    mock_llm_client.run_request = MagicMock(side_effect=lambda prompt: "mock_response")
    # Act
    core_features, overview, getting_started = mock_llm_client.get_responses()
    # Assert
    assert core_features == "mock_response"
    assert overview == "mock_response"
    assert getting_started == "mock_response"


def test_get_key_files(mock_llm_client):
    # Arrange
    mock_llm_client.run_request = MagicMock(return_value="mock_key_files_response")
    # Act
    key_files = mock_llm_client.get_key_files()
    # Assert
    assert key_files == ["mock_key_files_response"]
