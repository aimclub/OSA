import os
import re

from osa_tool.utils import logger


def read_file(file_path: str) -> str:
    """
    Reads the content of a file and returns it as a string.

    Args:
        file_path: The path to the file to be read.

    Returns:
        str: The content of the file as a string.
    """
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()


def save_sections(sections: str, path: str) -> None:
    """
    Saves the provided sections of text to a Markdown file.

    Args:
        sections: The content to be written to the file.
        path: The file path where the sections will be saved.
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(sections)


def extract_relative_paths(paths_string: str) -> list[str]:
    """
    Converts newline-separated paths into a list of normalized string paths.

    This function takes a multiline string, where each line is expected to be a file path,
    strips whitespace from each line, removes empty lines, and normalizes the paths using
    `os.path.normpath`.

    Args:
        paths_string: A string containing newline-separated file or directory paths.

    Returns:
        list[str]: Normalized relative paths.
    """
    try:
        return [
            os.path.normpath(line.strip())
            for line in paths_string.strip().splitlines()
            if line.strip()
        ]
    except Exception as e:
        logger.error(f"Failed to extract relative paths from model response: {e}")
        raise


def find_in_repo_tree(tree: str, pattern: str) -> str:
    """
    Searches for a pattern in the repository tree string and returns the first matching line.

    Args:
        tree: A string representation of the repository's file tree.
        pattern: The regular expression pattern to search for in the repository tree.

    Returns:
        str: The first line from the tree that matches the pattern. If no match is found, returns an empty string.
    """
    compiled_pattern = re.compile(pattern, re.IGNORECASE)

    for line in tree.split("\n"):
        if compiled_pattern.search(line):
            return line
    return ""
