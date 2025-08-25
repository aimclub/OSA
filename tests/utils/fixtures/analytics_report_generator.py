from unittest.mock import MagicMock, patch

import pytest

from osa_tool.analytics.report_generator import TextGenerator


@pytest.fixture
def text_generator_instance(mock_config_loader, mock_sourcerank, mock_repository_metadata):
    sourcerank_instance = mock_sourcerank()
    with (
        patch("osa_tool.analytics.report_generator.load_data_metadata", return_value=mock_repository_metadata),
        patch("osa_tool.analytics.report_generator.ModelHandlerFactory.build") as mock_model_handler_factory,
        patch("osa_tool.analytics.report_generator.extract_readme_content", return_value="Sample README content"),
        patch(
            "osa_tool.analytics.report_generator.tomllib.load",
            return_value={
                "prompt": {
                    "main_prompt": "{project_name} {metadata} {repository_tree} {presence_files} {readme_content}"
                }
            },
        ),
    ):
        mock_model_handler = MagicMock()
        mock_model_handler.send_request.return_value = (
            '{"repository_structure": "...", "readme_analysis": "...", "recommendations": "..."}'
        )

        mock_model_handler_factory.return_value = mock_model_handler

        yield TextGenerator(config_loader=mock_config_loader, sourcerank=sourcerank_instance), mock_model_handler
