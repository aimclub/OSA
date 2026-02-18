from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.context.article_content import PdfParser


@pytest.fixture
def mock_pdf_path(tmp_path):
    """
    Creates a temporary PDF file with dummy content and returns its path.
    
    Args:
        tmp_path: A pathlib.Path-like object representing a temporary directory.
    
    Returns:
        str: The filesystem path to the created dummy PDF file.
    """
    file_path = tmp_path / "test.pdf"
    file_path.write_text("dummy content")
    return str(file_path)


@pytest.fixture
def parser(mock_pdf_path):
    """
    Parse a PDF file and return a PdfParser instance.
    
    Args:
        mock_pdf_path: The path to the PDF file to be parsed.
    
    Returns:
        PdfParser: An instance of PdfParser initialized with the provided path.
    """
    return PdfParser(mock_pdf_path)


def test_data_extractor_filters_table_text(parser):
    """
    Test that the data extractor correctly filters out text located inside tables.
    
    Parameters
    ----------
    parser
        The parser instance whose :py:meth:`data_extractor` method is being tested.
    
    Returns
    -------
    None
        This function performs assertions and does not return a value.
    
    The test sets up a mock PDF document containing a single page with a table. It patches
    ``pdfplumber.open`` to return the mock document and patches
    ``extract_pages`` to provide a mock element with text that would normally appear
    inside the table. After invoking ``parser.data_extractor()``, the test asserts
    that the text "In table" is not present in the resulting output, confirming that
    the extractor properly excludes table contents.
    """
    # Arrange
    mock_table = MagicMock()
    mock_table.bbox = (0, 0, 500, 500)

    mock_page = MagicMock()
    mock_page.find_tables.return_value = [mock_table]

    mock_doc = MagicMock()
    mock_doc.pages = [mock_page]

    with patch("osa_tool.readmegen.context.article_content.pdfplumber.open") as mock_pdf_open:
        mock_pdf_open.return_value.__enter__.return_value = mock_doc

        mock_element = MagicMock()
        mock_element.get_text.return_value = "In table"
        mock_element.bbox = (100, 100, 200, 200)

        with patch("osa_tool.readmegen.context.article_content.extract_pages") as mock_extract_pages:
            mock_extract_pages.return_value = [[mock_element]]
            # Act
            result = parser.data_extractor()
            # Assert
            assert "In table" not in result, "Text inside table was not filtered out."


def test_is_table_text_lines_detects_text_inside_box():
    """
    Test that PdfParser.is_table_text_lines correctly detects a text line positioned inside a table box.
    
    This test sets up a mock PDF element with a bounding box that lies well within a rectangular region defined by two vertical and two horizontal lines. It then calls PdfParser.is_table_text_lines to verify that the method returns ``True`` for this scenario, indicating that the element is considered part of a table.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    None
    """
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
    """
    Test that PdfParser.is_table_text_standard returns True when an element's bounding box
    falls within a defined table box.
    
    This unit test creates a mock element with a specified bounding box and a list of
    table boxes. It then calls PdfParser.is_table_text_standard and asserts that the
    function correctly identifies the element as belonging to a standard table.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    mock_element = MagicMock()
    mock_element.bbox = (10, 10, 20, 20)

    table_boxes = [(0, 0, 30, 30)]
    # Act
    result = PdfParser.is_table_text_standard(mock_element, table_boxes)
    # Assert
    assert result is True


def test_is_table_text_standard_false():
    """
    Test that PdfParser.is_table_text_standard returns False when the element's bounding box does not overlap with any provided table boxes.
    
    This test creates a mock element with a bounding box that is far from a single table box. It then calls the static method `PdfParser.is_table_text_standard` with this element and the list of table boxes. The expected result is `False`, indicating that the element is not considered part of a standard table text region.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    None
    """
    # Arrange
    mock_element = MagicMock()
    mock_element.bbox = (100, 100, 200, 200)

    table_boxes = [(0, 0, 30, 30)]
    # Act
    result = PdfParser.is_table_text_standard(mock_element, table_boxes)
    # Assert
    assert result is False
