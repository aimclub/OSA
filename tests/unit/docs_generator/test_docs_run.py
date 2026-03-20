from unittest.mock import patch, MagicMock

from osa_tool.operations.docs.community_docs_generation.docs_run import generate_documentation


def test_generate_documentation_calls_builders_methods(mock_config_manager, mock_repository_metadata, caplog):
    """
    Tests that generate_documentation calls the expected builder methods.
    
    This test verifies that the generate_documentation function correctly
    instantiates the ContributingBuilder and CommunityTemplateBuilder classes
    and calls their respective build methods. It also checks for specific
    informational log messages.
    
    WHY: This test ensures the integration between the high-level documentation generation
    function and the underlying builder classes, confirming that all intended community
    and contribution documentation components are triggered.
    
    Args:
        mock_config_manager: Mock configuration manager object.
        mock_repository_metadata: Mock repository metadata object.
        caplog: Pytest fixture for capturing log output.
    
    Returns:
        None
    """
    with (
        patch(
            "osa_tool.operations.docs.community_docs_generation.docs_run.CommunityTemplateBuilder"
        ) as mock_community_cls,
        patch("osa_tool.operations.docs.community_docs_generation.docs_run.ContributingBuilder") as mock_contrib_cls,
    ):
        # Arrange
        mock_contributing_instance = MagicMock()
        mock_community_instance = MagicMock()

        mock_contributing_instance.build = MagicMock()
        mock_community_instance.build_code_of_conduct = MagicMock()
        mock_community_instance.build_pull_request = MagicMock()
        mock_community_instance.build_bug_issue = MagicMock()
        mock_community_instance.build_documentation_issue = MagicMock()
        mock_community_instance.build_feature_issue = MagicMock()

        mock_contrib_cls.return_value = mock_contributing_instance
        mock_community_cls.return_value = mock_community_instance
        caplog.set_level("INFO")

        # Act
        generate_documentation(mock_config_manager, mock_repository_metadata)

        # Assert
        assert "Starting generating additional documentation." in caplog.text
        assert "Additional documentation generation completed." in caplog.text

        mock_contributing_instance.build.assert_called_once()
        mock_community_instance.build_code_of_conduct.assert_called_once()
        mock_community_instance.build_pull_request.assert_called_once()
        mock_community_instance.build_bug_issue.assert_called_once()
        mock_community_instance.build_documentation_issue.assert_called_once()
        mock_community_instance.build_feature_issue.assert_called_once()
