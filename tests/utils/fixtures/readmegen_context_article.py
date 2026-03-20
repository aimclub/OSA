import os
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock

import pytest
from pdfminer.layout import LTTextContainer


@pytest.fixture
def mock_lt_element():
    """
    Creates a mock object representing an LTTextContainer element for testing purposes.
    This mock is used to simulate PDF layout elements in unit tests, allowing isolated testing of functions that process LTTextContainer objects without requiring actual PDF parsing.
    
    Args:
        None
    
    Returns:
        MagicMock: A mock object configured to mimic an LTTextContainer. It has:
            - A get_text() method that returns the string "Sample text".
            - A bbox attribute set to the tuple (0, 0, 10, 10), representing a typical bounding box (x0, y0, x1, y1).
    """
    element = MagicMock(spec=LTTextContainer)
    element.get_text.return_value = "Sample text"
    element.bbox = (0, 0, 10, 10)
    return element


@pytest.fixture
def temp_pdf_file():
    """
    Creates a temporary PDF file for testing purposes and cleans it up after use.
    
    This method generates a temporary file with a .pdf extension, writes a minimal PDF header to it, and yields the file path. Once the context is exited, the file is automatically deleted from the file system.
    
    Args:
        None
    
    Yields:
        str: The file system path to the temporary PDF file.
    
    Why:
        This method provides a clean, self-cleaning temporary file for unit tests or other operations that require a valid PDF file on disk. Using a context manager pattern ensures the file is removed after use, preventing leftover test files and maintaining a clean filesystem.
    """
    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(b"%PDF-1.4 test content")
        tmp.flush()
        yield tmp.name
    os.remove(tmp.name)
