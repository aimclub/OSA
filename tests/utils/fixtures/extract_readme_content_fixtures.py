from unittest.mock import patch

import pytest


@pytest.fixture
def mock_readme_content_aboutgen():
    with patch("osa_tool.aboutgen.about_generator.extract_readme_content", return_value="Sample README") as mock:
        yield mock
