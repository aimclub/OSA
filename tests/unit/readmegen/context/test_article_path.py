import os
from tempfile import NamedTemporaryFile
from unittest.mock import patch

import requests

from osa_tool.readmegen.context.article_path import get_pdf_path, fetch_pdf_from_url
from tests.utils.fixtures.article_fixtures import temp_pdf_file


def test_get_pdf_path_local_valid(temp_pdf_file):
    # Assert
    assert get_pdf_path(temp_pdf_file) == temp_pdf_file


def test_get_pdf_path_local_not_pdf():
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
    # Assert
    assert get_pdf_path("nonexistent.pdf") is None


@patch("osa_tool.readmegen.context.article_path.fetch_pdf_from_url", return_value="/tmp/fake.pdf")
def test_get_pdf_path_url_valid(mock_fetch):
    # Act
    result = get_pdf_path("http://example.com/file.pdf")

    # Assert
    assert result == "/tmp/fake.pdf"
    mock_fetch.assert_called_once()


@patch("osa_tool.readmegen.context.article_path.fetch_pdf_from_url", return_value=None)
def test_get_pdf_path_url_invalid(mock_fetch):
    # Act
    result = get_pdf_path("http://example.com/invalid.pdf")

    # Assert
    assert result is None
    mock_fetch.assert_called_once()


def test_fetch_pdf_from_url_success(tmp_path, mock_requests_response_factory):
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
    # Arrange
    mock_resp = mock_requests_response_factory(200, headers={"Content-Type": "text/html"})
    with patch("requests.get", return_value=mock_resp):
        # Act
        pdf_path = fetch_pdf_from_url("http://example.com/file.pdf")

    # Assert
    assert pdf_path is None


def test_fetch_pdf_from_url_404(mock_requests_response_factory):
    # Arrange
    mock_resp = mock_requests_response_factory(404, headers={"Content-Type": "application/pdf"})
    with patch("requests.get", return_value=mock_resp):
        # Act
        pdf_path = fetch_pdf_from_url("http://example.com/missing.pdf")

    # Assert
    assert pdf_path is None


def test_fetch_pdf_from_url_exception():
    # Arrange
    with patch("requests.get", side_effect=requests.exceptions.RequestException("Boom")):
        # Act
        pdf_path = fetch_pdf_from_url("http://example.com/error.pdf")

    # Assert
    assert pdf_path is None
