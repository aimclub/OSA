import json

import pytest

from osa_tool.readmegen.utils import (
    extract_example_paths,
    extract_relative_paths,
    find_in_repo_tree,
    read_file,
    read_ipynb_file,
    remove_extra_blank_lines,
    save_sections,
)


@pytest.fixture
def sample_tree():
    """
    Return a sample file tree representation as a multiline string.
    
    This function returns a hard‑coded string that lists a set of file paths
    representing a typical project structure. The paths are separated by
    newline characters and include Python modules, notebooks, documentation,
    and configuration files.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    str
        A multiline string containing the sample file tree.
    """
    return (
        "main.py\n"
        "subdir/utils.py\n"
        "examples/demo.py\n"
        "tutorials/intro.ipynb\n"
        "src/__init__.py\n"
        "examples/__init__.py\n"
        "notebooks/overview.ipynb\n"
        "docs/README.md\n"
        ".git/config"
    )


@pytest.fixture
def sample_notebook(tmp_path):
    """
    Creates a simple Jupyter notebook file in the specified temporary directory.
    
    This function generates a minimal notebook containing one markdown cell and one code cell,
    writes it to a file named ``sample.ipynb`` inside the provided ``tmp_path``, and returns
    the path to the created file.
    
    Args:
        tmp_path: A path-like object representing a temporary directory where the notebook
                  file will be created.
    
    Returns:
        The full path to the newly created ``sample.ipynb`` file.
    """
    file_path = tmp_path / "sample.ipynb"
    notebook = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Title\n", "Some text"]},
            {"cell_type": "code", "source": ["print('Hello, world!')\n"]},
        ]
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(notebook, f)
    return file_path


def test_read_ipynb_file(sample_notebook):
    """
    Test that `read_ipynb_file` correctly parses a Jupyter notebook file.
    
    Parameters
    ----------
    sample_notebook : Path
        Path to a sample Jupyter notebook file used for testing.
    
    Returns
    -------
    None
    
    This test reads the notebook file using `read_ipynb_file` and verifies that the
    returned content contains markers for markdown and code cells as well as the
    expected code snippet.
    """
    # Act
    content = read_ipynb_file(str(sample_notebook))
    # Assert
    assert "# --- MARKDOWN CELL ---" in content
    assert "# --- CODE CELL ---" in content
    assert "print('Hello, world!')" in content


def test_read_file_with_regular_text(tmp_path):
    """
    Test that `read_file` correctly reads a regular text file.
    
    Parameters
    ----------
    tmp_path
        Temporary directory path provided by pytest. The test creates a file
        named ``test.txt`` inside this directory, writes plain text to it,
        and then verifies that `read_file` returns the same content.
    
    Returns
    -------
    None
        The function performs an assertion and does not return a value.
    """
    # Arrange
    file_path = tmp_path / "test.txt"
    file_path.write_text("Some plain content", encoding="utf-8")
    # Act
    content = read_file(str(file_path))
    # Assert
    assert content == "Some plain content"


def test_read_file_ipynb(sample_notebook):
    """
    Test that read_file correctly reads an IPython notebook file.
    
    Args:
        sample_notebook: Path to a sample notebook file used for testing.
    
    Returns:
        None.
    
    This test reads the notebook file using the read_file function and verifies that the
    returned content contains expected markers for markdown and code cells.
    """
    # Act
    content = read_file(str(sample_notebook))
    # Assert
    assert "MARKDOWN CELL" in content
    assert "CODE CELL" in content


def test_save_sections(tmp_path):
    """
    Test that `save_sections` writes the provided content to the specified file path.
    
    Args:
        tmp_path: Temporary directory path provided by pytest for file creation.
    
    Returns:
        None
    """
    # Arrange
    target_file = tmp_path / "output.md"
    content = "# Section\nSome content"
    # Act
    save_sections(content, str(target_file))
    # Assert
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == content


def test_extract_relative_paths():
    """
    Test that `extract_relative_paths` correctly converts Windows-style paths to Unix-style relative paths.
    
    This test provides a list of file paths containing backslashes and verifies that the function returns the same paths with forward slashes, ensuring proper path normalization.
    
    Parameters:
        None
    
    Returns:
        None
    """
    # Arrange
    input_str = ["folder\\file.py\n", "folder2/test.py"]
    expected = ["folder/file.py", "folder2/test.py"]
    # Act
    result = extract_relative_paths(input_str)
    # Assert
    assert result == expected


def test_find_in_repo_tree(sample_tree):
    """
    Test that `find_in_repo_tree` correctly locates a file named ``utils`` within a repository tree.
    
    Args:
        sample_tree: A sample repository tree structure used as input for the test.
    
    Returns:
        None
    """
    # Act
    result = find_in_repo_tree(sample_tree, r"utils")
    # Assert
    assert result == "subdir/utils.py"


def test_extract_example_paths(sample_tree):
    """
    Test that `extract_example_paths` correctly identifies example files in a
    sample directory tree.
    
    This test verifies that the function returns a collection of file paths
    that include known example files such as ``examples/demo.py`` and
    ``tutorials/intro.ipynb``, while excluding non‑example files like
    ``__init__.py`` and files located in nested directories that should not
    be considered examples.
    
    Parameters
    ----------
    sample_tree
        A mock or fixture representing a directory tree structure that is
        passed to `extract_example_paths` to simulate a real file system.
    
    Returns
    -------
    None
        The function performs assertions and does not return a value.
    """
    # Act
    result = extract_example_paths(sample_tree)
    # Assert
    assert "examples/demo.py" in result
    assert "tutorials/intro.ipynb" in result
    assert "__init__.py" not in result
    assert "notebooks/tutorials/overview.ipynb" not in result


def test_remove_extra_blank_lines(tmp_path):
    """
    Test that the `remove_extra_blank_lines` function correctly collapses multiple consecutive blank lines in a markdown file.
    
    Parameters
    ----------
    tmp_path : pathlib.Path
        Temporary directory fixture provided by pytest to create a test file.
    
    Returns
    -------
    None
        This function performs assertions and does not return a value.
    """
    # Arrange
    path = tmp_path / "test.md"
    content = "Line 1\n\n\nLine 2\n\n\n\nLine 3"
    path.write_text(content, encoding="utf-8")
    # Act
    remove_extra_blank_lines(str(path))
    cleaned = path.read_text(encoding="utf-8")
    # Assert
    assert cleaned == "Line 1\n\nLine 2\n\nLine 3"
