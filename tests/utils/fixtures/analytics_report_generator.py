from unittest.mock import MagicMock, patch

import pytest

from osa_tool.analytics.report_generator import TextGenerator
from osa_tool.utils.prompts_builder import PromptLoader


@pytest.fixture
def text_generator_instance(mock_config_loader, mock_sourcerank, mock_repository_metadata):
    sourcerank_instance = mock_sourcerank()
    with (
        patch("osa_tool.analytics.report_generator.ModelHandlerFactory.build") as mock_model_handler_factory,
        patch("osa_tool.analytics.report_generator.extract_readme_content", return_value="Sample README content"),
    ):
        mock_model_handler = MagicMock()
        mock_model_handler.send_request.return_value = (
            '{"repository_structure": "...", "readme_analysis": "...", "recommendations": "..."}'
        )

        mock_model_handler_factory.return_value = mock_model_handler

        yield TextGenerator(
            config_loader=mock_config_loader,
            sourcerank=sourcerank_instance,
            prompts=PromptLoader(),
            metadata=mock_repository_metadata,
        ), mock_model_handler
