from unittest.mock import patch

import pytest

from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.readme_core import readme_agent


@pytest.fixture
def config_loader():
    config_loader = ConfigLoader()
    config_loader.config.git.repository = "https://github.com/user/test-repo"
    config_loader.config.git.name = "test-repo"
    return config_loader


@patch("osa_tool.readmegen.readme_core.remove_extra_blank_lines")
@patch("osa_tool.readmegen.readme_core.save_sections")
@patch("osa_tool.readmegen.readme_core.MarkdownBuilder")
@patch("osa_tool.readmegen.readme_core.LLMClient")
@patch("osa_tool.readmegen.readme_core.ReadmeRefiner")
def test_readme_agent_without_article(mock_refine, mock_llm, mock_builder, mock_save, mock_clean, config_loader):
    # Arrange
    mock_llm.return_value.get_responses.return_value = (
        "core_features_text",
        "overview_text",
        "getting_started_text",
    )
    mock_builder.return_value.build.return_value = "Final README content"
    mock_refine.return_value.refine.return_value = "Refined README content"

    # Act
    readme_agent(config_loader, article=None)

    # Assert
    mock_llm.return_value.get_responses.assert_called_once()
    mock_builder.assert_called_once_with(config_loader, "overview_text", "core_features_text", "getting_started_text")
    mock_builder.return_value.build.assert_called_once()
    mock_refine.assert_called_once_with(config_loader, "Final README content")
    mock_refine.return_value.refine.assert_called_once()
    mock_save.assert_called_once()
    mock_clean.assert_called_once()


@patch("osa_tool.readmegen.readme_core.remove_extra_blank_lines")
@patch("osa_tool.readmegen.readme_core.save_sections")
@patch("osa_tool.readmegen.readme_core.MarkdownBuilderArticle")
@patch("osa_tool.readmegen.readme_core.LLMClient")
def test_readme_agent_with_article(mock_llm, mock_builder_article, mock_save, mock_clean, config_loader):
    # Arrange
    article_path = "/path/to/article.pdf"
    mock_llm.return_value.get_responses_article.return_value = (
        "overview_from_article",
        "content_from_article",
        "algorithms_from_article",
    )

    mock_builder_article.return_value.build.return_value = "README from article"
    # Act
    readme_agent(config_loader, article=article_path)
    # Assert
    mock_llm.return_value.get_responses_article.assert_called_once_with(article_path)
    mock_builder_article.assert_called_once_with(
        config_loader,
        "overview_from_article",
        "content_from_article",
        "algorithms_from_article",
    )
    mock_builder_article.return_value.build.assert_called_once()
    mock_save.assert_called_once()
    mock_clean.assert_called_once()
