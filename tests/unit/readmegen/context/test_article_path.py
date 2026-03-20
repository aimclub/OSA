import os
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import requests

from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path, fetch_pdf_from_url


def test_get_pdf_path_local_valid(temp_pdf_file):
    """
    Tests that get_pdf_path returns the same path for a valid local PDF file.
    
    WHY: This test verifies that when a valid local PDF file path is provided to get_pdf_path, the function correctly identifies it as an existing local file and returns the same path unchanged, ensuring the validation logic for local files works as expected.
    
    Args:
        temp_pdf_file: A temporary PDF file path used for testing.
    
    Returns:
        None
    """
    # Assert
    assert get_pdf_path(temp_pdf_file) == temp_pdf_file


def test_get_pdf_path_local_not_pdf():
    """
    Tests that `get_pdf_path` returns `None` for a local file path that is not a PDF.
    
    This test creates a temporary text file (with a .txt extension) containing
    non-PDF content and verifies that the helper function `get_pdf_path` correctly
    identifies it as an invalid PDF source.
    
    WHY: The test ensures that `get_pdf_path` properly rejects local files that do not have a .pdf extension, which is a key validation step to prevent processing non-PDF files downstream.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    with NamedTemporaryFile(delete=False, suffix=".txt") as tmp:
        tmp.write(b"Not a PDF")
        tmp.flush()
        tmp_name = tmp.name
    # Assert
    try:
        assert get_pdf_path(tmp_name) is None
    # Cleanup
    finally:
        os.remove(tmp_name)


def test_get_pdf_path_local_missing():
    """
    Tests the behavior of get_pdf_path when given a non-existent local file path.
    
    Asserts that the function returns None for a file path that does not exist locally.
    This test ensures that the helper function correctly handles invalid local file inputs by returning None, preventing downstream errors when processing missing files.
    
    Args:
        None
    
    Returns:
        None
    """
    # Assert
    assert get_pdf_path("nonexistent.pdf") is None


@patch(
    "osa_tool.operations.docs.readme_generation.context.article_path.fetch_pdf_from_url", return_value="/tmp/fake.pdf"
)
def test_get_pdf_path_url_valid(mock_fetch):
    """
    Tests the get_pdf_path function with a valid URL input.
    
    This test verifies that when get_pdf_path is called with a valid URL,
    it returns the expected file path and that the external fetch function
    is called exactly once.
    
    WHY: To ensure the function correctly handles URL inputs by delegating to the fetch helper and returns the downloaded file path, while confirming the helper is invoked only once to avoid redundant network calls.
    
    Args:
        mock_fetch: A mocked version of the fetch_pdf_from_url function, injected via decorator to isolate the test from external dependencies.
    
    Returns:
        None
    """
    # Act
    result = get_pdf_path("http://example.com/file.pdf")

    # Assert
    assert result == "/tmp/fake.pdf"
    mock_fetch.assert_called_once()


@patch("osa_tool.operations.docs.readme_generation.context.article_path.fetch_pdf_from_url", return_value=None)
def test_get_pdf_path_url_invalid(mock_fetch):
    """
    Tests get_pdf_path with an invalid URL.
    
    This test verifies that get_pdf_path returns None when provided with a URL
    that cannot be fetched (as mocked to return None). It also checks that the
    underlying fetch function is called exactly once.
    
    WHY: To ensure the function properly handles network failures or invalid URLs by returning None and not attempting redundant fetch calls, which validates error-handling behavior and prevents downstream processing of invalid PDF sources.
    
    Args:
        mock_fetch: A mock object patching the fetch_pdf_from_url function, configured to return None to simulate a failed or invalid URL fetch.
    
    Returns:
        None
    """
    # Act
    result = get_pdf_path("http://example.com/invalid.pdf")

    # Assert
    assert result is None
    mock_fetch.assert_called_once()


def test_fetch_pdf_from_url_success(tmp_path, mock_requests_response_factory):
    """
    Tests the successful download of a PDF file from a URL.
    
    This test mocks a successful HTTP response with PDF content, calls the
    `fetch_pdf_from_url` function, and verifies that a valid PDF file is
    saved to the expected location.
    
    WHY: To ensure the download function correctly handles a valid PDF response,
    saves the file, and returns its path, confirming the core happy-path behavior.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path.
        mock_requests_response_factory: A pytest fixture providing a factory
            to create mock HTTP responses.
    
    Returns:
        None
    """
    # Arrange
    mock_resp = mock_requests_response_factory(
        200, headers={"Content-Type": "application/pdf"}, content_iter=lambda chunk_size: [b"%PDF-1.4 fake data"]
    )
    with patch("requests.get", return_value=mock_resp):
        # Act
        pdf_path = fetch_pdf_from_url("http://example.com/file.pdf")

    # Assert
    assert pdf_path is not None
    assert os.path.exists(pdf_path)
    with open(pdf_path, "rb") as f:
        assert b"%PDF-1.4" in f.read()

    # Cleanup
    os.remove(pdf_path)


def test_fetch_pdf_from_url_not_pdf(mock_requests_response_factory):
    """
    Tests that fetch_pdf_from_url returns None when the URL response is not a PDF.
    
    WHY: This verifies that the helper function correctly rejects non-PDF content by checking the Content-Type header, preventing the download and saving of invalid files (e.g., HTML pages) as PDFs.
    
    Args:
        mock_requests_response_factory: Fixture to provide a reusable mock response factory for requests.get.
    
    This test method does not return a value.
    """
    # Arrange
    mock_resp = mock_requests_response_factory(200, headers={"Content-Type": "text/html"})
    with patch("requests.get", return_value=mock_resp):
        # Act
        pdf_path = fetch_pdf_from_url("http://example.com/file.pdf")

    # Assert
    assert pdf_path is None


def test_fetch_pdf_from_url_404(mock_requests_response_factory):
    """
    Tests the behavior of fetch_pdf_from_url when the HTTP response status is 404.
    
    WHY: This test verifies that the function correctly handles "Not Found" errors by returning None, ensuring it does not attempt to save a non-existent or unavailable PDF.
    
    Args:
        mock_requests_response_factory: Fixture to provide a reusable mock response factory for requests.get.
    
    Returns:
        None
    """
    # Arrange
    mock_resp = mock_requests_response_factory(404, headers={"Content-Type": "application/pdf"})
    with patch("requests.get", return_value=mock_resp):
        # Act
        pdf_path = fetch_pdf_from_url("http://example.com/missing.pdf")

    # Assert
    assert pdf_path is None


def test_fetch_pdf_from_url_exception():
    """
    Tests the behavior of fetch_pdf_from_url when a network request exception occurs.
    
    This test simulates a scenario where the underlying HTTP request raises a RequestException. It verifies that the function returns None in such cases.
    
    WHY: This test ensures the fetch_pdf_from_url function gracefully handles network failures by returning None instead of propagating an exception, which aligns with its documented error-handling behavior.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    with patch("requests.get", side_effect=requests.exceptions.RequestException("Boom")):
        # Act
        pdf_path = fetch_pdf_from_url("http://example.com/error.pdf")

    # Assert
    assert pdf_path is None
