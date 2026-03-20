from unittest.mock import patch

from osa_tool.operations.docs.readme_generation.readme_core import ReadmeAgent


@patch("osa_tool.operations.docs.readme_generation.readme_core.remove_extra_blank_lines")
@patch("osa_tool.operations.docs.readme_generation.readme_core.save_sections")
@patch("osa_tool.operations.docs.readme_generation.readme_core.MarkdownBuilder")
@patch("osa_tool.operations.docs.readme_generation.readme_core.LLMClient")
def test_readme_agent_without_article(
    mock_llm,
    mock_builder,
    mock_save,
    mock_clean,
    mock_config_manager,
    mock_repository_metadata,
):
    """
    Test README generation without article (default mode).
    
    This unit test verifies that the ReadmeAgent correctly generates a README
    when no article attachment is provided (the default operational mode).
    It mocks the LLM client, Markdown builder, and file operations to isolate
    and validate the agent's internal logic and interactions.
    
    Args:
        mock_llm: Mock of the LLMClient, providing simulated LLM responses.
        mock_builder: Mock of the MarkdownBuilder, used to construct the README.
        mock_save: Mock of the save_sections function.
        mock_clean: Mock of the remove_extra_blank_lines function.
        mock_config_manager: Mock configuration manager for the agent.
        mock_repository_metadata: Mock repository metadata for the agent.
    
    The test sets up mock return values for LLM responses, README building,
    refinement, and cleaning steps. It then instantiates a ReadmeAgent with
    refinement enabled and calls generate_readme. Assertions verify that:
    1. The LLM is called to generate initial section texts.
    2. The builder is called with the correct texts and metadata.
    3. The built README is refined and cleaned by the LLM.
    4. The final content is saved and extra blank lines are removed.
    """

    # Arrange
    mock_llm.return_value.get_responses.return_value = (
        "core_features_text",
        "overview_text",
        "getting_started_text",
    )
    mock_builder.return_value.build.return_value = "Final README content"
    mock_llm.return_value.refine_readme.return_value = "Refined README content"
    mock_llm.return_value.clean.return_value = "Cleaned README content"

    agent = ReadmeAgent(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
        attachment=None,
        refine_readme=True,
    )

    # Act
    agent.generate_readme()

    # Assert
    mock_llm.return_value.get_responses.assert_called_once()
    mock_builder.assert_called_once_with(
        mock_config_manager,
        mock_repository_metadata,
        "overview_text",
        "core_features_text",
        "getting_started_text",
    )
    mock_builder.return_value.build.assert_called_once()
    mock_llm.return_value.refine_readme.assert_called_once_with("Final README content")
    mock_llm.return_value.clean.assert_called_once_with("Refined README content")
    mock_save.assert_called_once()
    mock_clean.assert_called_once()


@patch("osa_tool.operations.docs.readme_generation.readme_core.remove_extra_blank_lines")
@patch("osa_tool.operations.docs.readme_generation.readme_core.save_sections")
@patch("osa_tool.operations.docs.readme_generation.readme_core.MarkdownBuilderArticle")
@patch("osa_tool.operations.docs.readme_generation.readme_core.LLMClient")
def test_readme_agent_with_article(
    mock_llm,
    mock_builder_article,
    mock_save,
    mock_clean,
    mock_config_manager,
    mock_repository_metadata,
):
    """
    Test README generation with article (scientific mode).
    
    This unit test verifies that the ReadmeAgent correctly generates a README when provided with a scientific article as an attachment, operating in "scientific mode." It ensures the agent uses the article-specific LLM method to extract content, constructs the README via the article-specific builder, and skips refinement when `refine_readme=False`.
    
    Args:
        mock_llm: Mock of LLMClient, used to simulate responses from the language model.
        mock_builder_article: Mock of MarkdownBuilderArticle, used to simulate README construction.
        mock_save: Mock of save_sections, used to verify the README is saved.
        mock_clean: Mock of remove_extra_blank_lines, used to verify post-processing cleanup.
        mock_config_manager: Mock configuration manager for the agent.
        mock_repository_metadata: Mock repository metadata for the agent.
    
    The test sets up mocked return values for article-derived content, creates a ReadmeAgent with an article attachment and `refine_readme=False`, then calls `generate_readme`. Assertions verify that:
    - The LLM's article-specific method is called with the correct article path.
    - The article-specific builder is instantiated with the extracted content.
    - The builder's `build` method is invoked.
    - The refinement step is skipped.
    - The README is saved and cleaned as expected.
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

    agent = ReadmeAgent(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
        attachment=article_path,
        refine_readme=False,
    )

    # Act
    agent.generate_readme()

    # Assert
    mock_llm.return_value.get_responses_article.assert_called_once_with(article_path)
    mock_builder_article.assert_called_once_with(
        mock_config_manager,
        mock_repository_metadata,
        "overview_from_article",
        "content_from_article",
        "algorithms_from_article",
        "getting_started_from_article",
    )
    mock_builder_article.return_value.build.assert_called_once()
    mock_llm.return_value.refine_readme.assert_not_called()  # refine_readme=False
    mock_save.assert_called_once()
    mock_clean.assert_called_once()
