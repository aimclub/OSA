"""Utility functions for the repository organizer."""

import os
import re
import tempfile
from pathlib import Path
from typing import List

from osa_tool.utils.logger import logger


def atomic_write_file(path: Path, content: str) -> bool:
    """
    Atomically write content to a file using a temporary file.

    Args:
        path: Path to the file to write
        content: Content to write

    Returns:
        bool: True if write succeeded, False otherwise
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=".tmp_", delete=False
        ) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)
        os.replace(tmp_path, path)
        return True
    except Exception as e:
        logger.error("Failed to write %s atomically: %s", path, e)
        return False


def extract_error_files_advanced(error_output: str, base_path: Path, compiler_hint: str = None) -> List[str]:
    """
    Extract file paths from error output with compiler-specific handling.

    Args:
        error_output: Error output to parse
        base_path: Base path for resolving relative paths
        compiler_hint: Compiler hint for specialized parsing

    Returns:
        List[str]: List of extracted file paths
    """
    if compiler_hint == "gcc" or (compiler_hint is None and "gcc" in error_output.lower()):
        try:
            import json

            lines = error_output.strip().split("\n")
            for line in lines:
                if line.startswith("{"):
                    data = json.loads(line)
                    if "locations" in data:
                        files = set()
                        for loc in data["locations"]:
                            if "caret" in loc and "file" in loc["caret"]:
                                files.add(loc["caret"]["file"])
                            if "finish" in loc and "file" in loc["finish"]:
                                files.add(loc["finish"]["file"])
                        return [os.path.relpath(f, base_path) for f in files if Path(f).exists()]
        except:
            pass

    elif compiler_hint == "rust" or (compiler_hint is None and "rustc" in error_output.lower()):
        try:
            import json

            lines = error_output.strip().split("\n")
            for line in lines:
                if line.startswith("{"):
                    data = json.loads(line)
                    if "spans" in data:
                        files = set()
                        for span in data["spans"]:
                            if "file_name" in span:
                                files.add(span["file_name"])
                        return [os.path.relpath(f, base_path) for f in files if Path(f).exists()]
        except:
            pass

    return extract_error_files(error_output, base_path)


def extract_error_files(error_output: str, base_path: Path) -> List[str]:
    """
    Extract file paths from error output using regex patterns.

    Args:
        error_output: Error output to parse
        base_path: Base path for resolving relative paths

    Returns:
        List[str]: List of extracted file paths
    """
    file_paths = set()

    patterns = [
        r'File "([^"]+\.py)"',
        r"File '([^']+\.py)'",
        r"Error compiling \'([^\']+\.py)\'",
        r'File "([^"]+)", line \d+',
        r"([a-zA-Z]:\\[^:\s]+\.py)",
        r"(\.?[/\\][^:\s]+\.py)",
        r'([^"\s]+\.java):\d+',
        r'([^"\s]+\.go):\d+',
        r'([^"\s]+\.rs):\d+',
        r'([^"\s]+\.js):\d+',
        r'([^"\s]+\.ts):\d+',
        r'([^"\s]+\.c(?:pp)?):\d+',
        r'([^"\s]+\.h(?:pp)?):\d+',
        r'([^"\s]+\.cs):\d+',
        r'([^"\s]+\.swift):\d+',
        r'([^"\s]+\.rb):\d+',
        r'([^"\s]+\.kt):\d+',
    ]

    for pattern in patterns:
        for match in re.finditer(pattern, error_output, re.IGNORECASE):
            path = match.group(1)
            path = path.replace("\\", "/")
            try:
                abs_candidate = Path(path)
                if not abs_candidate.is_absolute():
                    full_candidate = base_path / path
                else:
                    full_candidate = abs_candidate

                if full_candidate.exists():
                    rel = os.path.relpath(full_candidate, start=str(base_path))
                    if not rel.startswith(".."):
                        file_paths.add(rel)
                else:
                    if not Path(path).is_absolute():
                        rel = path
                        rel = re.sub(r"^[./\\]+", "", rel)
                        if rel and not rel.startswith(".."):
                            file_paths.add(rel)
            except Exception as e:
                logger.debug("Error processing path '%s': %s", path, e)
                continue

    if file_paths:
        logger.debug("Extracted %d files from error output", len(file_paths))
    else:
        logger.warning("No files could be extracted from error output")

    return list(file_paths)
