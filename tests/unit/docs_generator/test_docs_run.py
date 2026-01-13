from unittest.mock import patch, MagicMock

from osa_tool.operations.docs.community_docs_generation.docs_run import generate_documentation


def test_generate_documentation_calls_builders_methods(mock_config_loader, mock_repository_metadata, caplog):
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
        generate_documentation(mock_config_loader, mock_repository_metadata)

        # Assert
        assert "Starting generating additional documentation." in caplog.text
        assert "All additional documentation successfully generated." in caplog.text

        mock_contributing_instance.build.assert_called_once()
        mock_community_instance.build_code_of_conduct.assert_called_once()
        mock_community_instance.build_pull_request.assert_called_once()
        mock_community_instance.build_bug_issue.assert_called_once()
        mock_community_instance.build_documentation_issue.assert_called_once()
        mock_community_instance.build_feature_issue.assert_called_once()
