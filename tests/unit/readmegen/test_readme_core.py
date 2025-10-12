from unittest.mock import patch

from osa_tool.readmegen.readme_core import readme_agent


@patch("osa_tool.readmegen.readme_core.remove_extra_blank_lines")
@patch("osa_tool.readmegen.readme_core.save_sections")
@patch("osa_tool.readmegen.readme_core.MarkdownBuilder")
@patch("osa_tool.readmegen.readme_core.LLMClient")
@patch("osa_tool.readmegen.readme_core.ReadmeRefiner")
def test_readme_agent_without_article(
    mock_refine, mock_llm, mock_builder, mock_save, mock_clean, mock_config_loader, mock_repository_metadata
):
    # Arrange
    mock_llm.return_value.get_responses.return_value = (
        "core_features_text",
        "overview_text",
        "getting_started_text",
    )
    mock_builder.return_value.build.return_value = "Final README content"
    mock_refine.return_value.refine.return_value = "Refined README content"

    # Act
    readme_agent(mock_config_loader, article=None, refine_readme=True, metadata=mock_repository_metadata)

    # Assert
    mock_llm.return_value.get_responses.assert_called_once()
    mock_builder.assert_called_once_with(
        mock_config_loader, mock_repository_metadata, "overview_text", "core_features_text", "getting_started_text"
    )
    mock_builder.return_value.build.assert_called_once()
    mock_refine.assert_called_once_with(mock_config_loader, "Final README content")
    mock_refine.return_value.refine.assert_called_once()
    mock_save.assert_called_once()
    mock_clean.assert_called_once()


@patch("osa_tool.readmegen.readme_core.remove_extra_blank_lines")
@patch("osa_tool.readmegen.readme_core.save_sections")
@patch("osa_tool.readmegen.readme_core.MarkdownBuilderArticle")
@patch("osa_tool.readmegen.readme_core.LLMClient")
def test_readme_agent_with_article(
    mock_llm, mock_builder_article, mock_save, mock_clean, mock_config_loader, mock_repository_metadata
):
    # Arrange
    article_path = "/path/to/article.pdf"
    mock_llm.return_value.get_responses_article.return_value = (
        "overview_from_article",
        "content_from_article",
        "algorithms_from_article",
        "getting_started_from_article",
    )

    mock_builder_article.return_value.build.return_value = "README from article"
    # Act
    readme_agent(mock_config_loader, article=article_path, refine_readme=False, metadata=mock_repository_metadata)
    # Assert
    mock_llm.return_value.get_responses_article.assert_called_once_with(article_path)
    mock_builder_article.assert_called_once_with(
        mock_config_loader,
        mock_repository_metadata,
        "overview_from_article",
        "content_from_article",
        "algorithms_from_article",
        "getting_started_from_article",
    )
    mock_builder_article.return_value.build.assert_called_once()
    mock_save.assert_called_once()
    mock_clean.assert_called_once()
