import os
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.context.article_path import fetch_pdf_from_url, get_pdf_path


@pytest.fixture
def mock_pdf_file():
    """
    Create a temporary PDF file for testing purposes.
    
    This generator function creates a temporary file with a `.pdf` suffix, writes minimal PDF
    content to it, yields the file path, and then removes the file after the caller has
    finished using it. It is intended for use in tests that require a PDF file on disk.
    
    Args:
        None
    
    Yields:
        str: The filesystem path to the temporary PDF file. The file is deleted after the
        generator is exhausted.
    
    Returns:
        None
    """
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(b"%PDF-1.4 test pdf content")
        temp_pdf_path = temp_file.name
    yield temp_pdf_path
    os.remove(temp_pdf_path)


@pytest.fixture
def mock_url_response():
    """
    Creates a mock HTTP response object for testing.
    
    This function constructs a MagicMock instance that mimics a
    response from an HTTP request. The mock is configured with a
    status code of 200, a Content-Type header indicating a PDF
    document, and an iter_content method that yields a single
    byte string representing a minimal PDF file.
    
    Returns:
        MagicMock: A mock response object with status_code, headers,
        and iter_content configured for a PDF payload.
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/pdf"}
    mock_response.iter_content.return_value = [b"%PDF-1.4 mock pdf content"]
    return mock_response


@patch("requests.get")
def test_get_pdf_path_url(mock_get, mock_url_response):
    """
    Test that `get_pdf_path` correctly downloads a PDF and returns a valid local path.
    
    Parameters
    ----------
    mock_get : object
        Mock object for `requests.get` injected by the `@patch("requests.get")` decorator.
    mock_url_response : object
        Mock response object returned by the patched `requests.get`.
    
    Returns
    -------
    None
        This test function does not return a value; it performs assertions to verify
        that a PDF file is downloaded, the returned path ends with '.pdf', and the
        file exists on disk. The temporary file is removed after the test.
    """
    # Arrange
    mock_get.return_value = mock_url_response
    url = "http://example.com/test.pdf"
    # Act
    pdf_path = get_pdf_path(url)
    # Assert
    assert pdf_path is not None
    assert pdf_path.endswith(".pdf")
    assert os.path.exists(pdf_path)
    # Teardown
    os.remove(pdf_path)


@patch("requests.get")
def test_get_pdf_path_invalid_url(mock_get):
    """
    Test that `get_pdf_path` returns `None` when the requested URL is not found (HTTP 404).
    
    Parameters
    ----------
    mock_get
        Mock object for `requests.get`, injected by the `@patch("requests.get")` decorator.
    
    Returns
    -------
    None
        This test function does not return a value; it asserts that `get_pdf_path` returns `None` for an invalid URL.
    """
    # Arrange
    mock_get.return_value = MagicMock(status_code=404)
    url = "http://example.com/invalid.pdf"
    # Act
    pdf_path = get_pdf_path(url)
    # Assert
    assert pdf_path is None


def test_get_pdf_path_file(mock_pdf_file):
    """
    Test that `get_pdf_path` returns the provided PDF file path and that the file exists.
    
    Args:
        mock_pdf_file: Path to a mock PDF file used for testing.
    
    Returns:
        None
    """
    # Act
    pdf_path = get_pdf_path(mock_pdf_file)
    # Assert
    assert pdf_path == mock_pdf_file
    assert os.path.exists(pdf_path)


def test_get_pdf_path_invalid_file():
    """
    Test that `get_pdf_path` returns `None` when given a non‑PDF file.
    
    This test creates a temporary text file in the current working directory,
    writes a non‑PDF string to it, and then calls `get_pdf_path` with the
    path to that file. It asserts that the function returns `None`, indicating
    that the file is not a valid PDF. Finally, it removes the temporary file
    to clean up.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    invalid_path = os.path.join(os.getcwd(), "test.txt")
    with open(invalid_path, "w") as f:
        f.write("This is not a PDF.")
    # Act
    pdf_path = get_pdf_path(invalid_path)
    # Assert
    assert pdf_path is None
    # Teardown
    os.remove(invalid_path)


@patch("requests.get")
def test_fetch_pdf_from_url_success(mock_get, mock_url_response):
    """
    Test that fetch_pdf_from_url successfully downloads a PDF from a given URL.
    
    Parameters
    ----------
    mock_get
        Mock object for requests.get patched by @patch decorator.
    mock_url_response
        Mock response object to be returned by the mocked requests.get call.
    
    Returns
    -------
    None
    """
    # Arrange
    mock_get.return_value = mock_url_response
    url = "http://example.com/test.pdf"
    # Act
    pdf_file_path = fetch_pdf_from_url(url)
    # Assert
    assert pdf_file_path is not None
    assert pdf_file_path.endswith(".pdf")
    assert os.path.exists(pdf_file_path)
    # Teardown
    os.remove(pdf_file_path)


@patch("requests.get")
def test_fetch_pdf_from_url_failure(mock_get):
    """
    Test that `fetch_pdf_from_url` correctly handles a 404 HTTP response by returning `None`.
    
    Parameters
    ----------
    mock_get
        Mock object for `requests.get` injected by the `@patch` decorator. It is configured to
        simulate a response with a 404 status code.
    
    Returns
    -------
    None
        This test function does not return a value; it asserts that the function under test
        behaves correctly when the requested PDF cannot be retrieved.
    """
    # Arrange
    mock_get.return_value = MagicMock(status_code=404)
    url = "http://example.com/invalid.pdf"
    # Act
    pdf_file_path = fetch_pdf_from_url(url)
    # Assert
    assert pdf_file_path is None
