from unittest.mock import patch

import pytest

from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.readme_core import readme_agent


@pytest.fixture
def config_loader():
    """
    Creates a ConfigLoader instance with predefined git repository and name.
    
    Returns:
        ConfigLoader: The configured ConfigLoader instance with `git.repository` set to
        "https://github.com/user/test-repo" and `git.name` set to "test-repo".
    """
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
    """
    Test the `readme_agent` function when no article is provided and the README
    is to be refined.
    
    This test verifies that the `readme_agent` correctly interacts with its
    dependencies when called with `article=None` and `refine_readme=True`.  It
    ensures that the language model client generates the expected section texts,
    the markdown builder constructs the final README content, the refiner
    processes that content, and the resulting sections are saved and cleaned.
    
    Parameters
    ----------
    mock_refine : MagicMock
        Mocked `ReadmeRefiner` class used to verify that the refiner is called
        with the correct arguments and that its `refine` method is invoked.
    mock_llm : MagicMock
        Mocked `LLMClient` class used to provide predetermined responses for
        the language model calls.
    mock_builder : MagicMock
        Mocked `MarkdownBuilder` class used to confirm that the builder receives
        the correct section texts and that its `build` method is called.
    mock_save : MagicMock
        Mocked `save_sections` function used to check that the final content is
        persisted.
    mock_clean : MagicMock
        Mocked `remove_extra_blank_lines` function used to verify that the
        content is cleaned before saving.
    config_loader : Any
        Configuration object passed to `readme_agent` that contains settings
        required by the function.
    
    Returns
    -------
    None
    """
    # Arrange
    mock_llm.return_value.get_responses.return_value = (
        "core_features_text",
        "overview_text",
        "getting_started_text",
    )
    mock_builder.return_value.build.return_value = "Final README content"
    mock_refine.return_value.refine.return_value = "Refined README content"

    # Act
    readme_agent(config_loader, article=None, refine_readme=True)

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
    """
    Test that the readme_agent correctly processes an article to generate a README.
    
    This test verifies that when an article path is supplied to `readme_agent`, the
    following sequence of interactions occurs:
    
    1. The LLM client is queried for article-specific responses.
    2. The Markdown builder is instantiated with those responses and used to
       build the README content.
    3. The resulting sections are saved and cleaned of extraneous blank lines.
    
    Parameters
    ----------
    mock_llm : Mock
        Mock object for the LLMClient used to simulate `get_responses_article`.
    mock_builder_article : Mock
        Mock object for the MarkdownBuilderArticle used to simulate README
        construction.
    mock_save : Mock
        Mock object for the `save_sections` function that persists the README.
    mock_clean : Mock
        Mock object for the `remove_extra_blank_lines` function that cleans the
        output.
    config_loader : Any
        Configuration loader passed to the readme_agent and the MarkdownBuilderArticle.
    
    Returns
    -------
    None
    """
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
    readme_agent(config_loader, article=article_path, refine_readme=False)
    # Assert
    mock_llm.return_value.get_responses_article.assert_called_once_with(article_path)
    mock_builder_article.assert_called_once_with(
        config_loader,
        "overview_from_article",
        "content_from_article",
        "algorithms_from_article",
        "getting_started_from_article",
    )
    mock_builder_article.return_value.build.assert_called_once()
    mock_save.assert_called_once()
    mock_clean.assert_called_once()
