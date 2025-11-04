import json
import os
import re

from osa_tool.logger import logger


def read_file(file_path: str) -> str:
    """
    Reads the content of a file and returns it as a string.

    Args:
        file_path: The path to the file to be read.

    Returns:
        str: The content of the file as a string.
    """
    if file_path.endswith(".ipynb"):
        return read_ipynb_file(file_path)

    if not os.path.isfile(file_path):
        logger.warning(f"File not found: {file_path}")
        return ""

    encodings_to_try = ["utf-8", "utf-16", "latin-1"]
    for encoding in encodings_to_try:
        try:
            with open(file_path, "r", encoding=encoding) as file:
                return file.read()
        except UnicodeDecodeError:
            continue

    logger.error(f"Failed to read {file_path} with any supported encoding")
    return ""


def read_ipynb_file(file_path: str) -> str:
    """
    Extracts and returns only code and markdown cells from a Jupyter notebook file.

    Args:
        file_path: The path to the .ipynb file.

    Returns:
        str: The extracted content from code and markdown cells.
            If an error occurs, returns an empty string.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)
        cells = notebook.get("cells", [])
        lines = []
        for cell in cells:
            cell_type = cell.get("cell_type")
            if cell_type in ("code", "markdown"):
                source = cell.get("source", [])
                lines.append(f"# --- {cell_type.upper()} CELL ---")
                lines.extend(source)
                lines.append("\n")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Failed to read notebook: {file_path}. Returning empty string. Error: {e}.")
        return ""


def save_sections(sections: str, path: str) -> None:
    """
    Saves the provided sections of text to a Markdown file.

    Args:
        sections: The content to be written to the file.
        path: The file path where the sections will be saved.
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(sections)


def extract_relative_paths(paths: list[str]) -> list[str]:
    """
    Converts a list of file or directory paths into a list of normalized relative paths.

    Args:
        paths: A list of file or directory paths.

    Returns:
        list[str]: A list of normalized relative paths.
    """
    try:
        return [os.path.normpath(path.strip()).replace("\\", "/") for path in paths if path.strip()]
    except Exception as e:
        logger.error(f"Failed to extract relative paths from model response: {e}")
        raise


def find_in_repo_tree(tree: str, pattern: str) -> str:
    """
    Searches for a pattern in the repository tree string and returns the first matching line.

    Args:
        tree: A string representation of the repository's file tree.
        pattern: A regular expression pattern to search for.

    Returns:
        str: The first matching line with normalized path separators,
             or an empty string if no match is found.
    """
    compiled_pattern = re.compile(pattern, re.IGNORECASE)

    for line in tree.split("\n"):
        if compiled_pattern.search(line):
            return line.replace("\\", "/")
    return ""


def extract_example_paths(tree: str):
    """
    Extracts paths from the repository tree that contain 'example' or 'tutorial' in their names.
    Args:
        tree: A string representation of the repository's file tree.

    Returns:
        list[str]: A list of matched paths excluding __init__.py files.
    """
    pattern = re.compile(r"\b(tutorials?|examples|docs?|documentation|wiki|manuals?)\b", re.IGNORECASE)
    result = []

    for line in tree.splitlines():
        line = line.strip()
        if not line or line.endswith("__init__.py"):
            continue
        if "." not in line.split("/")[-1]:
            continue
        if pattern.search(line):
            result.append(line)

    return result


def clean_code_block_indents(markdown_text: str) -> str:
    """
    Removes leading spaces before opening and closing fenced code blocks in markdown text.
    """
    opening_pattern = re.compile(r"^[ \t]+(```\w*)", re.MULTILINE)
    markdown_text = opening_pattern.sub(r"\1", markdown_text)

    closing_pattern = re.compile(r"^[ \t]+(```)$", re.MULTILINE)
    markdown_text = closing_pattern.sub(r"\1", markdown_text)

    return markdown_text


def remove_extra_blank_lines(path: str) -> None:
    """
    Cleans up extra blank lines from a file, leaving only single empty lines between content blocks.
    """
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cleaned_lines = []
    blank_line = False

    for line in lines:
        if line.strip() == "":
            if not blank_line:
                cleaned_lines.append("\n")
                blank_line = True
        else:
            cleaned_lines.append(line)
            blank_line = False

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(cleaned_lines)
