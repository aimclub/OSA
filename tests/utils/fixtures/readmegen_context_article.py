import os
from tempfile import NamedTemporaryFile
from unittest.mock import MagicMock

import pytest
from pdfminer.layout import LTTextContainer


@pytest.fixture
def mock_lt_element():
    element = MagicMock(spec=LTTextContainer)
    element.get_text.return_value = "Sample text"
    element.bbox = (0, 0, 10, 10)
    return element


@pytest.fixture
def temp_pdf_file():
    with NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(b"%PDF-1.4 test content")
        tmp.flush()
        yield tmp.name
    os.remove(tmp.name)
