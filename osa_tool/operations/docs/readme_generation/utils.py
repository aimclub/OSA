"""Shared file-I/O, tree-search, and markdown utilities for README generation."""

from __future__ import annotations

import json
import os
import re

from osa_tool.operations.docs.readme_generation.agent import ReadmeContext
from osa_tool.utils.logger import logger


def read_file(file_path: str) -> str:
    """Read *file_path* and return its text content (empty string on failure)."""
    if file_path.endswith(".ipynb"):
        return read_ipynb_file(file_path)

    if not os.path.isfile(file_path):
        logger.warning("File not found: %s", file_path)
        return ""

    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    logger.error("Failed to read %s with any supported encoding", file_path)
    return ""


def read_ipynb_file(file_path: str) -> str:
    """Extract code and markdown cells from a Jupyter notebook."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)
        lines: list[str] = []
        for cell in notebook.get("cells", []):
            cell_type = cell.get("cell_type")
            if cell_type in ("code", "markdown"):
                lines.append(f"# --- {cell_type.upper()} CELL ---")
                lines.extend(cell.get("source", []))
                lines.append("\n")
        return "\n".join(lines)
    except (OSError, json.JSONDecodeError):
        logger.error("Failed to read notebook: %s", file_path, exc_info=True)
        return ""


def save_sections(sections: str, path: str) -> None:
    """Write *sections* text to a Markdown file at *path*."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(sections)


def extract_relative_paths(paths: list[str]) -> list[str]:
    """Normalize a list of file paths to forward-slash relative paths."""
    try:
        return [os.path.normpath(p.strip()).replace("\\", "/") for p in paths if p.strip()]
    except (AttributeError, TypeError) as exc:
        logger.error("Failed to extract relative paths: %s", exc)
        raise


def find_in_repo_tree(tree: str, pattern: str) -> str:
    """Return the first line in *tree* matching *pattern* (case-insensitive), or ``""``."""
    compiled = re.compile(pattern, re.IGNORECASE)
    for line in tree.split("\n"):
        if compiled.search(line):
            return line.replace("\\", "/")
    return ""


def extract_example_paths(tree: str) -> list[str]:
    """Return file paths from *tree* containing example/tutorial/docs-related keywords."""
    pattern = re.compile(r"\b(tutorials?|examples|docs?|documentation|wiki|manuals?)\b", re.IGNORECASE)
    result: list[str] = []
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
    """Remove leading whitespace before fenced code-block delimiters."""
    text = re.sub(r"^[ \t]+(```\w*)", r"\1", markdown_text, flags=re.MULTILINE)
    text = re.sub(r"^[ \t]+(```)$", r"\1", text, flags=re.MULTILINE)
    return text


def remove_extra_blank_lines(path: str) -> None:
    """Collapse consecutive blank lines in a file to at most one."""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    cleaned: list[str] = []
    prev_blank = False
    for line in lines:
        if line.strip() == "":
            if not prev_blank:
                cleaned.append("\n")
                prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    with open(path, "w", encoding="utf-8") as f:
        f.writelines(cleaned)


def build_system_message(context: ReadmeContext, specific_key: str) -> str:
    """Compose base + node-specific."""
    parts = [
        context.prompts.get("readme.system_messages.base"),
        context.prompts.get(f"readme.system_messages.{specific_key}"),
    ]
    return "\n\n".join(p for p in parts if p and p.strip())
