import pytest

from osa_tool.utils import extract_readme_content


@pytest.mark.parametrize(
    "readme_name,expected_content",
    [
        ("README.md", "# Hello"),
        ("README.rst", "Project description"),
        ("README_en.rst", "English doc"),
    ],
)
def test_extract_readme_content_found(tmp_path, readme_name, expected_content):
    # Arrange
    readme_path = tmp_path / readme_name
    readme_path.write_text(expected_content, encoding="utf-8")
    # Assert
    assert extract_readme_content(str(tmp_path)) == expected_content


def test_extract_readme_content_not_found(tmp_path):
    # Assert
    assert extract_readme_content(str(tmp_path)) == "No README.md file"
