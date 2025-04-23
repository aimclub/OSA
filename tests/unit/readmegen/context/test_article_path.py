import os
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.context.article_path import fetch_pdf_from_url, get_pdf_path


@pytest.fixture
def mock_pdf_file():
    with NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
        temp_file.write(b'%PDF-1.4 test pdf content')
        temp_pdf_path = temp_file.name
    yield temp_pdf_path
    os.remove(temp_pdf_path)


@pytest.fixture
def mock_url_response():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {'Content-Type': 'application/pdf'}
    mock_response.iter_content.return_value = [b'%PDF-1.4 mock pdf content']
    return mock_response


@patch('requests.get')
def test_get_pdf_path_url(mock_get, mock_url_response):
    # Arrange
    mock_get.return_value = mock_url_response
    url = "http://example.com/test.pdf"
    # Act
    pdf_path = get_pdf_path(url)
    # Assert
    assert pdf_path is not None
    assert pdf_path.endswith('.pdf')
    assert os.path.exists(pdf_path)
    # Teardown
    os.remove(pdf_path)


@patch('requests.get')
def test_get_pdf_path_invalid_url(mock_get):
    # Arrange
    mock_get.return_value = MagicMock(status_code=404)
    url = "http://example.com/invalid.pdf"
    # Act
    pdf_path = get_pdf_path(url)
    # Assert
    assert pdf_path is None


def test_get_pdf_path_file(mock_pdf_file):
    # Act
    pdf_path = get_pdf_path(mock_pdf_file)
    # Assert
    assert pdf_path == mock_pdf_file
    assert os.path.exists(pdf_path)


def test_get_pdf_path_invalid_file():
    # Arrange
    invalid_path = os.path.join(os.getcwd(), 'test.txt')
    with open(invalid_path, 'w') as f:
        f.write('This is not a PDF.')
    # Act
    pdf_path = get_pdf_path(invalid_path)
    # Assert
    assert pdf_path is None
    # Teardown
    os.remove(invalid_path)


@patch('requests.get')
def test_fetch_pdf_from_url_success(mock_get, mock_url_response):
    # Arrange
    mock_get.return_value = mock_url_response
    url = "http://example.com/test.pdf"
    # Act
    pdf_file_path = fetch_pdf_from_url(url)
    # Assert
    assert pdf_file_path is not None
    assert pdf_file_path.endswith('.pdf')
    assert os.path.exists(pdf_file_path)
    # Teardown
    os.remove(pdf_file_path)


@patch('requests.get')
def test_fetch_pdf_from_url_failure(mock_get):
    # Arrange
    mock_get.return_value = MagicMock(status_code=404)
    url = "http://example.com/invalid.pdf"
    # Act
    pdf_file_path = fetch_pdf_from_url(url)
    # Assert
    assert pdf_file_path is None
