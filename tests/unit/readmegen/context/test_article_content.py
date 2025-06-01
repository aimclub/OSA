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


@patch("osa_tool.readmegen.context.article_content.extract_pages")
@patch("osa_tool.readmegen.context.article_content.ap.Document")
def test_data_extractor_filters_table_text(mock_doc_class, mock_extract_pages, parser):
    mock_doc = MagicMock()
    mock_doc.pages = [MagicMock()]
    mock_doc_class.return_value = mock_doc

    mock_table_rect = MagicMock(llx=0, lly=0, urx=500, ury=500)
    mock_table = MagicMock(rectangle=mock_table_rect)

    with patch(
        "osa_tool.readmegen.context.article_content.ap.text.TableAbsorber"
    ) as mock_absorber_class:
        absorber_instance = mock_absorber_class.return_value
        absorber_instance.visit.return_value = None
        absorber_instance.table_list = [mock_table]

        mock_element_in_table = MagicMock()
        mock_element_in_table.get_text.return_value = "In table"
        mock_element_in_table.bbox = (100, 100, 200, 200)

        mock_extract_pages.return_value = [[mock_element_in_table]]

        result = parser.data_extractor()
        assert "In table" not in result


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
