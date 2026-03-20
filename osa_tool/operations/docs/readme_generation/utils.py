import json
import os
import re

from osa_tool.utils.logger import logger


def read_file(file_path: str) -> str:
    """
    Reads the content of a file and returns it as a string.
    
    Handles both regular text files and Jupyter notebook (.ipynb) files. For notebook files, only code and markdown cells are extracted and formatted. If the file does not exist, logs a warning and returns an empty string. The method attempts to decode the file using several common encodings (UTF-8, UTF-16, Latin-1) to handle different text formats gracefully. If all decoding attempts fail, logs an error and returns an empty string.
    
    Args:
        file_path: The path to the file to be read.
    
    Returns:
        str: The content of the file as a string. Returns an empty string if the file is not found, cannot be decoded, or an error occurs during reading.
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
    
    The method reads a Jupyter notebook (.ipynb) file, filters its cells to include only those of type "code" or "markdown", and formats them into a single string. This is useful for extracting the executable and explanatory content from a notebook while ignoring other cell types (e.g., raw cells), making the content suitable for further processing or documentation.
    
    Args:
        file_path: The path to the .ipynb file.
    
    Returns:
        str: The extracted content from code and markdown cells, formatted with headers indicating each cell type. If an error occurs during reading or parsing, returns an empty string and logs the error.
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
        sections: The content to be written to the file. This should be a single string containing the full Markdown content.
        path: The file path where the sections will be saved. The file will be created or overwritten.
    
    Why:
        This method provides a simple, consistent way to write Markdown content to a file with UTF-8 encoding, ensuring compatibility with special characters and international text.
    """
    with open(path, "w", encoding="utf-8") as file:
        file.write(sections)


def extract_relative_paths(paths: list[str]) -> list[str]:
    """
    Converts a list of file or directory paths into a list of normalized relative paths.
    
    Paths are normalized to use forward slashes as separators, regardless of the original format, and any leading/trailing whitespace is removed. Empty or whitespace-only entries are filtered out.
    
    Args:
        paths: A list of file or directory paths. Each path is stripped of whitespace; empty strings after stripping are ignored.
    
    Returns:
        list[str]: A list of normalized relative paths using forward slashes.
    
    Why:
        This normalization ensures consistent path formatting across different operating systems (e.g., converting Windows backslashes to forward slashes) and removes invalid entries, which is critical for downstream processing that expects clean, uniform path strings.
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
        tree: A string representation of the repository's file tree, typically a multi-line string.
        pattern: A regular expression pattern to search for. The search is case-insensitive.
    
    Returns:
        str: The first matching line with normalized path separators (backslashes replaced by forward slashes),
             or an empty string if no match is found.
    
    Why:
        This method is used to locate files or directories within a repository tree representation by matching a regex pattern.
        Normalizing path separators ensures consistent formatting across different operating systems.
    """
    compiled_pattern = re.compile(pattern, re.IGNORECASE)

    for line in tree.split("\n"):
        if compiled_pattern.search(line):
            return line.replace("\\", "/")
    return ""


def extract_example_paths(tree: str):
    """
    Extracts paths from the repository tree that contain terms like 'example', 'tutorial', or related documentation keywords in their names.
    This is used to identify documentation, example, and tutorial files for further processing or reporting in the OSA Tool.
    
    Args:
        tree: A string representation of the repository's file tree, where each line is a file path.
    
    Returns:
        A list of matched file paths. Paths are excluded if they are empty lines, end with '__init__.py', or if the last component (filename) does not contain a dot (likely indicating a directory). Only paths matching the pattern are included.
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
    
    WHY: In Markdown, leading spaces before fenced code block markers (```) can cause the code block to be interpreted as a code block within a list or as indented text, breaking proper rendering. This method ensures fenced code blocks are correctly recognized by removing unintended indentation.
    
    Args:
        markdown_text: The markdown text containing fenced code blocks that may have leading spaces.
    
    Returns:
        The markdown text with leading spaces removed from lines that start with opening or closing fenced code block markers.
    """
    opening_pattern = re.compile(r"^[ \t]+(```\w*)", re.MULTILINE)
    markdown_text = opening_pattern.sub(r"\1", markdown_text)

    closing_pattern = re.compile(r"^[ \t]+(```)$", re.MULTILINE)
    markdown_text = closing_pattern.sub(r"\1", markdown_text)

    return markdown_text


def remove_extra_blank_lines(path: str) -> None:
    """
    Cleans up extra blank lines from a file, leaving only single empty lines between content blocks.
    
    WHY: This method ensures consistent formatting by removing excessive blank lines, which can clutter files and make them harder to read, while preserving intentional single blank lines that separate logical content blocks.
    
    Args:
        path: The file path to process.
    
    Returns:
        None. The file is modified in-place.
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


def format_time(seconds: float) -> str:
    """
    Convert seconds into a human-readable HH:MM:SS format.
    
    Args:
        seconds: The total number of seconds to format. Non‑integer values are truncated to an integer before conversion.
    
    Returns:
        A string in the format HH:MM:SS, where hours, minutes, and seconds are zero‑padded to two digits each.
        For example, 3665 seconds becomes "01:01:05".
    """
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
