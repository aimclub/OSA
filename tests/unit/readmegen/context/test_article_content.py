from unittest.mock import MagicMock, patch

from pdfminer.layout import LTTextContainer

from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser


@patch("osa_tool.operations.docs.readme_generation.context.article_content.pdfplumber.open")
@patch("osa_tool.operations.docs.readme_generation.context.article_content.extract_pages")
def test_basic_text_extraction(mock_extract_pages, mock_pdfplumber_open, mock_lt_element, tmp_path):
    """
    Verifies that the PdfParser correctly extracts basic text from a PDF file using mocked PDF elements.
    
    This test ensures the PdfParser's data_extractor method can retrieve text from a simple PDF when no table content is present. It mocks both pdfminer and pdfplumber dependencies to isolate the parser's logic and avoid actual file I/O.
    
    Args:
        mock_extract_pages: Mock object for the pdfminer extract_pages function.
        mock_pdfplumber_open: Mock object for the pdfplumber open function.
        mock_lt_element: Mock object representing a layout element within a PDF page.
        tmp_path: A pytest fixture providing a temporary directory path for creating dummy files.
    
    Returns:
        None.
    """
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
    """
    Verifies that the data_extractor method ignores text segments that are too short.
    
    This test mocks a PDF element containing a short string ("abc") and ensures that the
    parser filters it out, resulting in an empty string return value. It uses patches to
    simulate the PDF extraction process and bypass table detection logic.
    
    Why: The PdfParser is designed to filter out very short text segments (like "abc") 
    because they are likely to be non‑content artifacts (e.g., page numbers, stray 
    characters) that would add noise to the extracted text.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path used to simulate
            the existence of a PDF file. The test creates a dummy PDF file path from it.
    
    Returns:
        None.
    """
    # Arrange
    element = MagicMock(spec=LTTextContainer)
    element.get_text.return_value = "abc"
    element.bbox = (0, 0, 1, 1)

    with (
        patch("osa_tool.operations.docs.readme_generation.context.article_content.pdfplumber.open") as mock_open,
        patch(
            "osa_tool.operations.docs.readme_generation.context.article_content.extract_pages", return_value=[[element]]
        ),
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
    """
    Verify that text lines identified as table content are ignored during data extraction.
    
    This test mocks a PDF structure where elements are flagged as table text lines. It ensures that the `data_extractor` method filters out these elements, resulting in an empty string return value.
    The test patches PDF parsing dependencies to simulate a scenario where `PdfParser.is_table_text_lines` returns True, causing the parser to treat the content as part of a table and exclude it from extraction.
    
    Args:
        mock_lt_element: A mocked layout element representing content within a PDF page.
        tmp_path: A pytest fixture providing a temporary directory for creating dummy file paths.
    
    Returns:
        None.
    """
    # Arrange
    pdf_file = tmp_path / "sample.pdf"
    pdf_file.write_text("dummy content")

    with (
        patch("osa_tool.operations.docs.readme_generation.context.article_content.pdfplumber.open") as mock_open,
        patch(
            "osa_tool.operations.docs.readme_generation.context.article_content.extract_pages",
            return_value=[[mock_lt_element]],
        ),
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
    """
    Verifies that the PDF file is successfully deleted from the file system after the data extraction process is completed.
    
    WHY: This test ensures that the PdfParser cleans up the temporary PDF file it processes, preventing leftover files and confirming proper resource management.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path used to create the dummy PDF file.
    
    Returns:
        This method does not return a value; it asserts that the file no longer exists.
    """
    # Arrange
    pdf_file = tmp_path / "downloaded_sample.pdf"
    pdf_file.write_text("dummy content")

    element = MagicMock(spec=LTTextContainer)
    element.get_text.return_value = "Some text"
    element.bbox = (0, 0, 10, 10)

    with (
        patch("osa_tool.operations.docs.readme_generation.context.article_content.pdfplumber.open") as mock_open,
        patch(
            "osa_tool.operations.docs.readme_generation.context.article_content.extract_pages", return_value=[[element]]
        ),
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
