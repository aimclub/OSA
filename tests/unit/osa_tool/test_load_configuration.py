from unittest.mock import patch, MagicMock

from osa_tool.run import load_configuration


@patch("osa_tool.readmeai.config.settings.ConfigLoader", autospec=True)
@patch("osa_tool.utils.osa_project_root", return_value="/mock/project/root")
def test_load_configuration_without_article(mock_project_root, mock_loader):
    # Arrange
    mock_config = MagicMock()
    mock_loader.return_value = mock_config
    # Act
    config = load_configuration("https://github.com/example/repo", "openai",
                                "https://api.openai.com", "gpt-4", None)
    # Assert
    assert config.config.git.repository == "https://github.com/example/repo"
    assert config.config.llm.api == "openai"
    assert config.config.llm.url == "https://api.openai.com"
    assert config.config.llm.model == "gpt-4"


@patch("osa_tool.readmeai.readmegen_article.config.settings.ArticleConfigLoader", autospec=True)
@patch("osa_tool.utils.osa_project_root", return_value="/mock/project/root")
def test_load_configuration_with_article(mock_project_root, mock_loader):
    # Arrange
    mock_config = MagicMock()
    mock_loader.return_value = mock_config
    # Act
    config = load_configuration("https://github.com/example/repo", "openai",
                                "https://api.openai.com", "gpt-4", "article.pdf")
    # Assert
    assert config.config.git.repository == "https://github.com/example/repo"
    assert config.config.llm.api == "openai"
    assert config.config.llm.url == "https://api.openai.com"
    assert config.config.llm.model == "gpt-4"
