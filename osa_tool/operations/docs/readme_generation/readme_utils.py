"""Shared file-I/O, tree-search, and markdown utilities for README generation."""

import os
import re

from osa_tool.operations.docs.readme_generation.pipeline.runtime_context import ReadmeContext
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import read_file, read_ipynb_file  # noqa: F401  (re-exported)


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


def to_repo_relative_link(rel_path: str, *, from_dir: str = "") -> str:
    """Convert a repo-relative target path to a markdown link from *from_dir* (relative to repo root)."""
    if not rel_path:
        return ""
    target = rel_path.replace("\\", "/").lstrip("./")
    source = from_dir.replace("\\", "/").strip("./").strip("/") or "."
    link = os.path.relpath(target, start=source).replace("\\", "/")
    if not link.startswith("."):
        link = f"./{link}"
    return link


def to_readme_relative_link(rel_path: str) -> str:
    """Convert a repo-relative path to a link from the project-root README (``./...``)."""
    return to_repo_relative_link(rel_path)


def find_in_repo_tree(tree: str, pattern: str, *, prefer_directory: bool = False) -> str:
    """Return the first line in *tree* matching *pattern* (case-insensitive), or ``""``."""
    compiled = re.compile(pattern, re.IGNORECASE)
    matches: list[str] = []
    for line in tree.split("\n"):
        if not line.strip():
            continue
        normalized = line.replace("\\", "/")
        if compiled.search(normalized):
            matches.append(normalized)
    if not matches:
        return ""
    if not prefer_directory:
        return matches[0]
    return min(matches, key=lambda path: (path.count("/"), path))


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
