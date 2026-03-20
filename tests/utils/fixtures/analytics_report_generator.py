from unittest.mock import MagicMock, patch

import pytest

from osa_tool.operations.analysis.repository_report.report_generator import TextGenerator


@pytest.fixture
def text_generator_instance(mock_config_manager, mock_repository_metadata):
    """
    Creates a pytest fixture providing an instance of TextGenerator and a mocked model handler.
    
    This method mocks the ModelHandlerFactory and README content extraction to facilitate isolated testing of the TextGenerator class. It yields a tuple containing the initialized TextGenerator and its associated mock model handler.
    
    Args:
        mock_config_manager: The mocked configuration manager instance.
        mock_repository_metadata: The mocked repository metadata instance.
    
    Yields:
        tuple: A tuple containing the TextGenerator instance and the MagicMock model handler.
    
    Why:
        The fixture mocks the external dependencies (ModelHandlerFactory and extract_readme_content) to isolate the TextGenerator for unit testing. This ensures tests are not affected by the actual model handler implementation or real README content, providing a controlled environment.
    """
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
