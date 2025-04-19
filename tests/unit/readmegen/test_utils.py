import json

import pytest

from osa_tool.readmegen.utils import (
    extract_example_paths,
    extract_relative_paths,
    find_in_repo_tree,
    read_file,
    read_ipynb_file,
    remove_extra_blank_lines,
    save_sections
)


@pytest.fixture
def sample_tree():
    return (
        "main.py\n"
        "subdir/utils.py\n"
        "examples/demo.py\n"
        "tutorials/intro.ipynb\n"
        "src/__init__.py\n"
        "examples/__init__.py\n"
        "notebooks/tutorials/overview.ipynb\n"
        "docs/README.md\n"
        ".git/config"
    )


@pytest.fixture
def sample_notebook(tmp_path):
    file_path = tmp_path / "sample.ipynb"
    notebook = {
        "cells": [
            {"cell_type": "markdown", "source": ["# Title\n", "Some text"]},
            {"cell_type": "code", "source": ["print('Hello, world!')\n"]}
        ]
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(notebook, f)
    return file_path


def test_read_ipynb_file(sample_notebook):
    # Act
    content = read_ipynb_file(str(sample_notebook))
    # Assert
    assert "# --- MARKDOWN CELL ---" in content
    assert "# --- CODE CELL ---" in content
    assert "print('Hello, world!')" in content


def test_read_file_with_regular_text(tmp_path):
    # Arrange
    file_path = tmp_path / "test.txt"
    file_path.write_text("Some plain content", encoding="utf-8")
    # Act
    content = read_file(str(file_path))
    # Assert
    assert content == "Some plain content"


def test_read_file_ipynb(sample_notebook):
    # Act
    content = read_file(str(sample_notebook))
    # Assert
    assert "MARKDOWN CELL" in content
    assert "CODE CELL" in content


def test_save_sections(tmp_path):
    # Arrange
    target_file = tmp_path / "output.md"
    content = "# Section\nSome content"
    # Act
    save_sections(content, str(target_file))
    # Assert
    assert target_file.exists()
    assert target_file.read_text(encoding="utf-8") == content


def test_extract_relative_paths():
    # Arrange
    input_str = "folder/file.py\nfolder2/test.py\n\n"
    expected = ["folder/file.py", "folder2/test.py"]
    # Act
    result = extract_relative_paths(input_str)
    # Assert
    assert result == expected


def test_find_in_repo_tree(sample_tree):
    # Act
    result = find_in_repo_tree(sample_tree, r"utils")
    # Assert
    assert result == "subdir/utils.py"


def test_extract_example_paths(sample_tree):
    # Act
    result = extract_example_paths(sample_tree)
    # Assert
    assert "examples/demo.py" in result
    assert "tutorials/intro.ipynb" in result
    assert "__init__.py" not in result
    assert "notebooks/tutorials/overview.ipynb" not in result


def test_remove_extra_blank_lines(tmp_path):
    # Arrange
    path = tmp_path / "test.md"
    content = "Line 1\n\n\nLine 2\n\n\n\nLine 3"
    path.write_text(content, encoding="utf-8")
    # Act
    remove_extra_blank_lines(str(path))
    cleaned = path.read_text(encoding="utf-8")
    # Assert
    assert cleaned == "Line 1\n\nLine 2\n\nLine 3"
