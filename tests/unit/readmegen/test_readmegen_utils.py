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
    # Arrange
    file_path = tmp_path / "test.txt"
    file_path.write_text("hello world", encoding="utf-8")

    # Act
    content = read_file(str(file_path))

    # Assert
    assert content == "hello world"


def test_read_file_not_found(caplog):
    # Act
    content = read_file("nonexistent.txt")

    # Assert
    assert content == ""
    assert "File not found" in caplog.text


def test_read_file_wrong_encoding(tmp_path):
    # Arrange
    file_path = tmp_path / "test.bin"
    file_path.write_bytes(b"\xff\xfe\x00\x00")

    # Act
    content = read_file(str(file_path))

    # Assert
    assert isinstance(content, str)


def test_read_ipynb_file_code_and_markdown(tmp_path):
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
    # Arrange
    file_path = tmp_path / "broken.ipynb"
    file_path.write_text("{not-valid-json", encoding="utf-8")

    # Act
    result = read_ipynb_file(str(file_path))

    # Assert
    assert result == ""
    assert "Failed to read notebook" in caplog.text


def test_save_sections(tmp_path):
    # Arrange
    path = tmp_path / "out.md"

    # Act
    save_sections("## section", str(path))

    # Assert
    assert path.read_text(encoding="utf-8") == "## section"


def test_extract_relative_paths_ok():
    # Arrange
    input_paths = [" foo/bar ", "a\\b\\c", ""]

    # Act
    result = extract_relative_paths(input_paths)
    # Assert
    assert result == ["foo/bar", "a/b/c"]


def test_extract_relative_paths_error(monkeypatch):
    # Arrange
    def broken_normpath(path):
        raise RuntimeError("fail")

    monkeypatch.setattr(os.path, "normpath", broken_normpath)

    # Assert
    with pytest.raises(RuntimeError):
        extract_relative_paths(["abc"])


def test_find_in_repo_tree_match():
    # Arrange
    tree = get_mock_repo_tree("FULL")

    # Act
    result = find_in_repo_tree(tree, r"readme")

    # Assert
    assert result == "README.md"


def test_find_in_repo_tree_no_match():
    # Arrange
    tree = get_mock_repo_tree("MINIMAL")

    # Act
    result = find_in_repo_tree(tree, r"notfound")

    # Assert
    assert result == ""


def test_extract_example_paths():
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
    # Arrange
    md = "    ```python\nprint(1)\n    ```"

    # Act
    cleaned = clean_code_block_indents(md)

    # Assert
    assert cleaned.startswith("```python")
    assert cleaned.strip().endswith("```")


def test_remove_extra_blank_lines(tmp_path):
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
