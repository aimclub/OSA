import json
import os

import pytest

from osa_tool.operations.docs.readme_generation.utils import (
    read_file,
    read_ipynb_file,
    save_sections,
    extract_relative_paths,
    find_in_repo_tree,
    clean_code_block_indents,
    remove_extra_blank_lines,
    extract_example_paths,
)
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_read_file_text(tmp_path):
    """
    Tests the read_file function by reading a text file and verifying its content.
    
    This test ensures that read_file correctly reads and returns the content of a plain text file. It uses a temporary file to isolate the test and avoid side effects.
    
    Args:
        tmp_path: A temporary directory path provided by pytest for test isolation.
    
    Returns:
        None
    """
    # Arrange
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello world", encoding="utf-8")

    # Act
    content = read_file(str(file_path))

    # Assert
    assert content == "hello world"


def test_read_file_not_found(caplog):
    """
    Tests the behavior of read_file when the specified file does not exist.
    
    This test verifies that read_file returns an empty string and logs an appropriate warning when the target file is missing. It ensures the function gracefully handles file-not-found errors as specified in its documentation.
    
    Args:
        caplog: A pytest fixture for capturing log messages.
    
    Returns:
        None
    """
    # Act
    content = read_file("nonexistent.txt")

    # Assert
    assert content == ""
    assert "File not found" in caplog.text


def test_read_file_wrong_encoding(tmp_path):
    """
    Tests that read_file handles a file with an invalid encoding gracefully.
    
    This test verifies that when read_file encounters bytes that cannot be decoded using its standard fallback encodings (UTF-8, UTF-16, Latin-1), it still returns a string result (specifically an empty string) rather than raising an exception. The test writes raw bytes (specifically a UTF-32 BOM) to a temporary file to simulate an unsupported or invalid encoding scenario.
    
    Args:
        tmp_path: A temporary directory path fixture provided by pytest.
    
    Returns:
        None
    """
    # Arrange
    file_path = tmp_path / "test.bin"
    file_path.write_bytes(b"\xff\xfe\x00\x00")

    # Act
    content = read_file(str(file_path))

    # Assert
    assert isinstance(content, str)


def test_read_ipynb_file_code_and_markdown(tmp_path):
    """
    Tests the read_file function's ability to parse a Jupyter notebook file.
    
    This test verifies that read_file correctly extracts code and markdown cells
    from a .ipynb file while ignoring other cell types (e.g., raw cells). It
    creates a temporary notebook file with a mix of cell types and asserts that
    the returned content contains the expected markers for code and markdown
    cells and excludes the content from ignored cells.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path object
            for creating test files.
    
    Why:
        The test ensures that the helper function read_file properly filters and formats notebook cells,
        which is critical for accurately extracting only relevant content (code and markdown) from Jupyter notebooks
        during repository analysis and documentation generation.
    """
    # Arrange
    nb = {
        "cells": [
            {"cell_type": "code", "source": ["print(1)\n"]},
            {"cell_type": "markdown", "source": ["# Title\n"]},
            {"cell_type": "raw", "source": ["not included\n"]},
        ]
    }
    file_path = tmp_path / "test.ipynb"
    file_path.write_text(json.dumps(nb), encoding="utf-8")

    # Act
    content = read_file(str(file_path))

    # Assert
    assert "# --- CODE CELL ---" in content
    assert "# --- MARKDOWN CELL ---" in content
    assert "not included" not in content


def test_read_ipynb_file_error(tmp_path, caplog):
    """
    Tests that read_ipynb_file returns an empty string and logs an error when given a malformed .ipynb file.
    
    This test verifies the error‑handling behavior of read_ipynb_file when the input file contains invalid JSON. The method is expected to return an empty string and log an appropriate error message, ensuring that malformed notebook files do not cause the calling code to crash.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path for creating test files.
        caplog: A pytest fixture for capturing log messages.
    
    Returns:
        None
    """
    # Arrange
    file_path = tmp_path / "broken.ipynb"
    file_path.write_text("{not-valid-json", encoding="utf-8")

    # Act
    result = read_ipynb_file(str(file_path))

    # Assert
    assert result == ""
    assert "Failed to read notebook" in caplog.text


def test_save_sections(tmp_path):
    """
    Tests the save_sections function by writing a section header to a file.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path object.
    
    Why:
        This test verifies that the save_sections function correctly writes the provided Markdown content to a specified file path using UTF-8 encoding. It ensures the function creates or overwrites the file as expected and that the written content matches exactly what was supplied.
    
    Steps:
        1. Arrange: Creates a temporary file path for the output.
        2. Act: Calls save_sections with a sample section header and the file path.
        3. Assert: Confirms the file's content equals the provided section header.
    """
    # Arrange
    path = tmp_path / "out.md"

    # Act
    save_sections("## section", str(path))

    # Assert
    assert path.read_text(encoding="utf-8") == "## section"


def test_extract_relative_paths_ok():
    """
    Tests the extract_relative_paths function with valid input.
    
    Verifies that the function correctly normalizes a list of mixed-format
    paths (including spaces and backslashes) and filters out empty strings.
    
    Why:
    This test ensures the helper function properly handles typical edge cases
    like extra whitespace and different path separators, confirming it produces
    clean, normalized results suitable for cross-platform use.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    input_paths = [" foo/bar ", "a\\b\\c", ""]

    # Act
    result = extract_relative_paths(input_paths)
    # Assert
    assert result == ["foo/bar", "a/b/c"]


def test_extract_relative_paths_error(monkeypatch):
    """
    Tests that extract_relative_paths propagates an error from os.path.normpath.
    
    This test verifies that when os.path.normpath raises an exception, the extract_relative_paths function does not catch it but instead allows the error to propagate to the caller.
    
    Args:
        monkeypatch: Pytest fixture used to mock system functions.
    
    Why:
        Ensuring error propagation is important for maintaining predictable error handling and allowing callers to react appropriately to underlying system failures, such as filesystem errors or invalid path operations.
    """
    # Arrange
    def broken_normpath(path):
        raise RuntimeError("fail")

    monkeypatch.setattr(os.path, "normpath", broken_normpath)

    # Assert
    with pytest.raises(RuntimeError):
        extract_relative_paths(["abc"])


def test_find_in_repo_tree_match():
    """
    Tests the find_in_repo_tree function for a successful match.
    
    This test verifies that find_in_repo_tree correctly identifies and returns
    the first line matching a given pattern within a mock repository tree.
    
    Why:
        This test ensures the search functionality works as expected when a match exists,
        confirming that the pattern matching and line retrieval behave correctly in a
        controlled environment using a mock repository tree.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    tree = get_mock_repo_tree("FULL")

    # Act
    result = find_in_repo_tree(tree, r"readme")

    # Assert
    assert result == "README.md"


def test_find_in_repo_tree_no_match():
    """
    Tests the scenario where find_in_repo_tree returns an empty string when no match is found.
    
    Args:
        None
    
    Returns:
        None
    
    Why:
        This test verifies that find_in_repo_tree correctly returns an empty string when the provided regular expression pattern does not match any line in the repository tree. This ensures the function behaves as expected for non-matching searches, which is important for error handling and control flow in calling code.
    """
    # Arrange
    tree = get_mock_repo_tree("MINIMAL")

    # Act
    result = find_in_repo_tree(tree, r"notfound")

    # Assert
    assert result == ""


def test_extract_example_paths():
    """
    Tests the extract_example_paths function.
    
    This test verifies that the function correctly extracts file paths containing
    'example' or 'tutorial' from a given repository tree string, while excluding
    any __init__.py files and directories (paths without a dot in the filename).
    
    The test uses a predefined tree string with various file paths to ensure the
    function filters correctly, including both positive and negative assertions.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    tree = """
    src/main.py
    docs/guide.md
    examples/example1.py
    tests/test_a.py
    examples/__init__.py
    """

    # Act
    result = extract_example_paths(tree)

    # Assert
    assert "docs/guide.md" in result
    assert "examples/example1.py" in result
    assert all("__init__.py" not in r for r in result)


def test_clean_code_block_indents():
    """
    Tests the clean_code_block_indents function with a markdown string containing indented code blocks.
        
    This method verifies that the helper function correctly removes leading spaces
    from fenced code block markers, ensuring the cleaned output starts and ends
    with proper code block delimiters.
    
    WHY: This test ensures that markdown with indented code blocks—which can be misinterpreted by parsers—is properly cleaned so that code blocks are correctly recognized and rendered.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    md = "    ```python\nprint(1)\n    ```"

    # Act
    cleaned = clean_code_block_indents(md)

    # Assert
    assert cleaned.startswith("```python")
    assert cleaned.strip().endswith("```")


def test_remove_extra_blank_lines(tmp_path):
    """
    Tests the remove_extra_blank_lines function on a file with multiple consecutive blank lines.
    
    WHY: This test verifies that the helper function correctly reduces multiple consecutive blank lines to single blank lines, ensuring consistent formatting without removing intentional single blank lines that separate content.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path object.
    
    Returns:
        None
    """
    # Arrange
    path = tmp_path / "file.md"
    content = "line1\n\n\nline2\n\nline3\n"
    path.write_text(content, encoding="utf-8")

    # Act
    remove_extra_blank_lines(str(path))
    cleaned = path.read_text(encoding="utf-8")

    # Assert
    assert "\n\n\n" not in cleaned
    assert "line1" in cleaned and "line2" in cleaned and "line3" in cleaned
