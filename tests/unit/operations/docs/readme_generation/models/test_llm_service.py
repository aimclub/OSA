from osa_tool.core.models.llm_output_models import LlmTextOutput


def test_get_citation_from_readme_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=[LlmTextOutput(text="Some citation")])

    # Act
    result = llm_client.get_citation_from_readme()

    # Assert
    assert result == "Some citation"


def test_get_article_name_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=[LlmTextOutput(text="Deep Learning Paper")])

    # Act
    result = llm_client.get_article_name("pdf_content")

    # Assert
    assert result == "Deep Learning Paper"
