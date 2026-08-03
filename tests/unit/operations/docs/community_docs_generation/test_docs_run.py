from unittest.mock import patch, MagicMock

from osa_tool.operations.docs.community_docs_generation.docs_run import generate_documentation


def test_generate_documentation_calls_builders_methods(mock_config_manager, mock_repository_metadata, caplog):
    with (
        patch(
            "osa_tool.operations.docs.community_docs_generation.docs_run.CommunityTemplateBuilder"
        ) as mock_community_cls,
        patch("osa_tool.operations.docs.community_docs_generation.docs_run.ContributingBuilder") as mock_contrib_cls,
    ):
        # Arrange
        mock_contributing_instance = MagicMock()
        mock_community_instance = MagicMock()
        mock_community_instance.host = "github"
        call_order = []

        mock_contrib_cls.side_effect = lambda *_: call_order.append("contributing_init") or mock_contributing_instance
        mock_contributing_instance.build = MagicMock(side_effect=lambda: call_order.append("contributing_build"))
        mock_community_cls.side_effect = lambda *_: call_order.append("community_init") or mock_community_instance
        mock_community_instance.build_code_of_conduct = MagicMock()
        mock_community_instance.build_security = MagicMock()
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
        assert call_order == ["contributing_init", "contributing_build", "community_init"]

        mock_contributing_instance.build.assert_called_once()
        mock_community_instance.build_code_of_conduct.assert_called_once()
        mock_community_instance.build_security.assert_called_once()
        mock_community_instance.build_pull_request.assert_called_once()
        mock_community_instance.build_bug_issue.assert_called_once()
        mock_community_instance.build_documentation_issue.assert_called_once()
        mock_community_instance.build_feature_issue.assert_called_once()


def test_generate_documentation_links_pr_template_to_generated_contributing(
    mock_config_manager, mock_repository_metadata, tmp_path
):
    repo_dir = tmp_path / "local_repo"
    repo_dir.mkdir()
    git = mock_config_manager.config.git
    git.repository = repo_dir
    git.host = None
    git.host_domain = None
    git.full_name = f"local/{repo_dir.name}"
    mock_repository_metadata.clone_url_http = ""
    mock_repository_metadata.issues_url = ""

    generate_documentation(mock_config_manager, mock_repository_metadata)

    pr_template = repo_dir / ".github" / "PULL_REQUEST_TEMPLATE.md"
    assert "I read the contributing document at ./CONTRIBUTING.md" in pr_template.read_text(encoding="utf-8")
