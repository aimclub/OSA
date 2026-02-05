from unittest.mock import MagicMock, patch

import pytest

from osa_tool.operations.analysis.repository_report.report_generator import TextGenerator


@pytest.fixture
def text_generator_instance(mock_config_manager, mock_repository_metadata):
    with (
        patch(
            "osa_tool.operations.analysis.repository_report.report_generator.ModelHandlerFactory.build"
        ) as mock_model_handler_factory,
        patch(
            "osa_tool.operations.analysis.repository_report.report_generator.extract_readme_content",
            return_value="Sample README content",
        ),
    ):
        mock_model_handler = MagicMock()
        mock_model_handler.send_request.return_value = (
            '{"repository_structure": "...", "readme_analysis": "...", "recommendations": "..."}'
        )

        mock_model_handler_factory.return_value = mock_model_handler

        yield TextGenerator(
            config_manager=mock_config_manager,
            metadata=mock_repository_metadata,
        ), mock_model_handler
