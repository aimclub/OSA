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
    """
    Test that `extract_readme_content` correctly reads the content of a README file when it exists.
    
    Parameters
    ----------
    tmp_path
        A temporary directory path provided by pytest.
    readme_name
        The filename of the README to create in the temporary directory.
    expected_content
        The text content to write to the README file and the content expected to be returned by
        `extract_readme_content`.
    
    Returns
    -------
    None
        This test function does not return a value; it asserts that the extracted content matches
        the expected content.
    """
    # Arrange
    readme_path = tmp_path / readme_name
    readme_path.write_text(expected_content, encoding="utf-8")
    # Assert
    assert extract_readme_content(str(tmp_path)) == expected_content


def test_extract_readme_content_not_found(tmp_path):
    """
    Test that `extract_readme_content` returns a default message when no README.md file is found.
    
    Args:
        tmp_path: A temporary directory path provided by pytest.
    
    Returns:
        None
    """
    # Assert
    assert extract_readme_content(str(tmp_path)) == "No README.md file"
