from unittest import mock

from osa_tool.docs_generator.docs_run import generate_documentation


@mock.patch("osa_tool.docs_generator.docs_run.CommunityTemplateBuilder")
@mock.patch("osa_tool.docs_generator.docs_run.ContributingBuilder")
@mock.patch("osa_tool.docs_generator.docs_run.logger")
def test_generate_documentation(
    mock_logger, mock_contributing_builder, mock_community_builder, config_loader
):
    # Arrange
    # Create mocks for the configuration and all builders
    mock_contributing = mock.MagicMock()
    mock_contributing_builder.return_value = mock_contributing
    mock_community = mock.MagicMock()
    mock_community_builder.return_value = mock_community
    # Mock build methods
    mock_contributing.build = mock.MagicMock()
    mock_community.build_code_of_conduct = mock.MagicMock()
    mock_community.build_pull_request = mock.MagicMock()
    mock_community.build_bug_issue = mock.MagicMock()
    mock_community.build_documentation_issue = mock.MagicMock()
    mock_community.build_feature_issue = mock.MagicMock()

    # Act
    generate_documentation(config_loader)
    # Assert
    # Check that Con
    mock_contributing.build.assert_called_once()

    # Check that CommunityTemplateBuilder methods were called
    mock_community.build_code_of_conduct.assert_called_once()
    mock_community.build_pull_request.assert_called_once()
    mock_community.build_bug_issue.assert_called_once()
    mock_community.build_documentation_issue.assert_called_once()
    mock_community.build_feature_issue.assert_called_once()

    # Check that the logs contain the correct call
    mock_logger.info.assert_any_call("Starting generating additional documentation.")
    mock_logger.info.assert_any_call(
        "All additional documentation successfully generated."
    )
