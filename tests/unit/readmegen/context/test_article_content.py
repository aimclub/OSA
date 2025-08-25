from unittest.mock import MagicMock, patch

from pdfminer.layout import LTTextContainer

from osa_tool.readmegen.context.article_content import PdfParser


@patch("osa_tool.readmegen.context.article_content.pdfplumber.open")
@patch("osa_tool.readmegen.context.article_content.extract_pages")
def test_basic_text_extraction(mock_extract_pages, mock_pdfplumber_open, mock_lt_element, tmp_path):
    # Arrange
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_text("dummy content")

    mock_doc = MagicMock()
    mock_doc.pages = []
    mock_pdfplumber_open.return_value.__enter__.return_value = mock_doc

    mock_extract_pages.return_value = [[mock_lt_element]]

    with (
        patch.object(PdfParser, "is_table_text_lines", return_value=False),
        patch.object(PdfParser, "is_table_text_standard", return_value=False),
    ):
        parser = PdfParser(str(pdf_file))

        # Act
        text = parser.data_extractor()

    # Assert
    assert "Sample text" in text


def test_ignore_short_text(tmp_path):
    # Arrange
    element = MagicMock(spec=LTTextContainer)
    element.get_text.return_value = "abc"
    element.bbox = (0, 0, 1, 1)

    with (
        patch("osa_tool.readmegen.context.article_content.pdfplumber.open") as mock_open,
        patch("osa_tool.readmegen.context.article_content.extract_pages", return_value=[[element]]),
        patch.object(PdfParser, "is_table_text_lines", return_value=False),
        patch.object(PdfParser, "is_table_text_standard", return_value=False),
    ):
        mock_doc = MagicMock()
        mock_doc.pages = []
        mock_open.return_value.__enter__.return_value = mock_doc
        parser = PdfParser(str(tmp_path / "dummy.pdf"))

        # Act
        result = parser.data_extractor()

    # Assert
    assert result == ""


def test_ignore_table_text_lines(mock_lt_element, tmp_path):
    # Arrange
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_text("dummy content")

    with (
        patch("osa_tool.readmegen.context.article_content.pdfplumber.open") as mock_open,
        patch("osa_tool.readmegen.context.article_content.extract_pages", return_value=[[mock_lt_element]]),
        patch.object(PdfParser, "is_table_text_lines", return_value=True),
        patch.object(PdfParser, "is_table_text_standard", return_value=False),
    ):
        mock_doc = MagicMock()
        mock_doc.pages = []
        mock_open.return_value.__enter__.return_value = mock_doc

        parser = PdfParser(str(pdf_file))

        # Act
        result = parser.data_extractor()

    # Assert
    assert result == ""


def test_file_removal(tmp_path):
    # Arrange
    pdf_file = tmp_path / "downloaded_sample.pdf"
    pdf_file.write_text("dummy content")

    element = MagicMock(spec=LTTextContainer)
    element.get_text.return_value = "Some text"
    element.bbox = (0, 0, 10, 10)

    with (
        patch("osa_tool.readmegen.context.article_content.pdfplumber.open") as mock_open,
        patch("osa_tool.readmegen.context.article_content.extract_pages", return_value=[[element]]),
        patch.object(PdfParser, "is_table_text_lines", return_value=False),
        patch.object(PdfParser, "is_table_text_standard", return_value=False),
    ):
        mock_doc = MagicMock()
        mock_doc.pages = []
        mock_open.return_value.__enter__.return_value = mock_doc
        parser = PdfParser(str(pdf_file))

        # Act
        _ = parser.data_extractor()

    # Assert
    assert not pdf_file.exists()
