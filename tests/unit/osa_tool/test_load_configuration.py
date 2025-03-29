import pytest
from unittest.mock import patch, MagicMock

from osa_tool.run import load_configuration


@pytest.mark.parametrize(
    "repo_url, api, api_url, model, article,"
    "expected_repo, expected_api, expected_url, expected_model",
    [
        ("https://github.com/example/repo", "openai", "https://api.openai.com", "gpt-test", None,
         "https://github.com/example/repo", "openai", "https://api.openai.com", "gpt-test"),
        ("https://github.com/example/repo", "openai", "https://api.openai.com", "gpt-test-article", "article.pdf",
         "https://github.com/example/repo", "openai", "https://api.openai.com", "gpt-test-article")
    ]
)
@patch("osa_tool.utils.osa_project_root", return_value="/mock/project/root")
@patch("osa_tool.readmeai.config.settings.ConfigLoader", autospec=True)
@patch("osa_tool.readmeai.readmegen_article.config.settings.ArticleConfigLoader", autospec=True)
def test_load_configuration(mock_article_loader, mock_config_loader, mock_project_root,
                            repo_url, api, api_url, model, article,
                            expected_repo, expected_api, expected_url, expected_model):
    # Arrange
    mock_config = MagicMock()
    mock_config_loader.return_value = mock_config
    mock_article_loader.return_value = mock_config
    # Act
    config = load_configuration(repo_url, api, api_url, model, article)
    # Assert
    assert config.config.git.repository == expected_repo
    assert config.config.llm.api == expected_api
    assert config.config.llm.url == expected_url
    assert config.config.llm.model == expected_model
