from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.context.article_content import PdfParser


@pytest.fixture
def mock_pdf_path(tmp_path):
    file_path = tmp_path / "test.pdf"
    file_path.write_text("dummy content")
    return str(file_path)


@pytest.fixture
def parser(mock_pdf_path):
    return PdfParser(mock_pdf_path)


def test_data_extractor_filters_table_text(parser):
    # Arrange
    mock_table = MagicMock()
    mock_table.bbox = (0, 0, 500, 500)

    mock_page = MagicMock()
    mock_page.find_tables.return_value = [mock_table]

    mock_doc = MagicMock()
    mock_doc.pages = [mock_page]

    with patch(
        "osa_tool.readmegen.context.article_content.pdfplumber.open"
    ) as mock_pdf_open:
        mock_pdf_open.return_value.__enter__.return_value = mock_doc

        mock_element = MagicMock()
        mock_element.get_text.return_value = "In table"
        mock_element.bbox = (100, 100, 200, 200)

        with patch(
            "osa_tool.readmegen.context.article_content.extract_pages"
        ) as mock_extract_pages:
            mock_extract_pages.return_value = [[mock_element]]
            # Act
            result = parser.data_extractor()
            # Assert
            assert "In table" not in result, "Text inside table was not filtered out."


def test_is_table_text_lines_detects_text_inside_box():
    # Arrange
    verticals = [(100, 100, 100, 300), (200, 100, 200, 300)]
    horizontals = [(100, 100, 200, 100), (100, 300, 200, 300)]

    mock_element = MagicMock()
    mock_element.bbox = (120, 150, 180, 180)  # Center is clearly inside
    # Act
    result = PdfParser.is_table_text_lines(mock_element, verticals, horizontals)
    # Assert
    assert result is True


def test_is_table_text_standard_true():
    # Arrange
    mock_element = MagicMock()
    mock_element.bbox = (10, 10, 20, 20)

    table_boxes = [(0, 0, 30, 30)]
    # Act
    result = PdfParser.is_table_text_standard(mock_element, table_boxes)
    # Assert
    assert result is True


def test_is_table_text_standard_false():
    # Arrange
    mock_element = MagicMock()
    mock_element.bbox = (100, 100, 200, 200)

    table_boxes = [(0, 0, 30, 30)]
    # Act
    result = PdfParser.is_table_text_standard(mock_element, table_boxes)
    # Assert
    assert result is False
