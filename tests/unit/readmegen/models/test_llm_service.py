from unittest.mock import patch

import pytest


def test_get_key_files_returns_list(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=['{"key_files": ["src/main.py", "README.md"]}'])

    with patch("osa_tool.readmegen.models.llm_service.process_text") as mock_process:
        mock_process.side_effect = lambda x: x

        # Act
        result = llm_client.get_key_files()

    # Assert
    assert result == ["src/main.py", "README.md"]


def test_get_key_files_invalid_json_raises(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["not a json"])

    with patch("osa_tool.readmegen.models.llm_service.process_text") as mock_process:
        mock_process.side_effect = lambda x: x

        # Assert
        with pytest.raises(ValueError):
            llm_client.get_key_files()


def test_get_responses_article_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(
        side_effect=[
            '{"key_files": ["src/main.py", "README.md"]}',  # get_key_files
            "files_summary",  # files summary
            "pdf_summary",  # pdf summary
            "overview_article",  # overview
            "content_article",  # content
            "algorithms_article",  # algorithms
            "getting_started_article",  # getting_started
        ]
    )

    with (
        patch("osa_tool.readmegen.models.llm_service.process_text") as mock_process,
        patch("osa_tool.readmegen.context.article_path.get_pdf_path") as mock_pdf_path,
        patch("osa_tool.readmegen.context.article_content.PdfParser.data_extractor") as mock_pdf_extract,
    ):

        mock_process.side_effect = lambda x: x
        mock_pdf_path.return_value = "fake_path.pdf"
        mock_pdf_extract.return_value = "pdf_content"

        # Act
        overview, content, algorithms, getting_started = llm_client.get_responses_article("article.pdf")

    # Assert
    assert overview == "overview_article"
    assert content == "content_article"
    assert algorithms == "algorithms_article"
    assert getting_started == "getting_started_article"


def test_deduplicate_sections_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["deduplicated"])

    with patch("osa_tool.readmegen.models.llm_service.process_text") as mock_process:
        mock_process.side_effect = lambda x: x

        # Act
        result = llm_client.deduplicate_sections("installation", "getting_started")

    # Assert
    assert result == "deduplicated"


def test_refine_readme_returns_expected(llm_client, mock_model_handler):
    # Arrange
    llm_client.model_handler = mock_model_handler(side_effect=["refined_readme"])

    with patch("osa_tool.readmegen.models.llm_service.process_text") as mock_process:
        mock_process.side_effect = lambda x: x

        # Act
        result = llm_client.refine_readme({"section": "content"})

    # Assert
    assert result == "refined_readme"
