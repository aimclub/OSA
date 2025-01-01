"""Filter files based on a default ignore list."""

from pathlib import Path


def is_excluded(ignore_list: dict, file_path: Path, repo_path: Path) -> bool:
    """Check if the file should be ignored based on the ignore list."""
    relative_path = file_path.relative_to(repo_path)

    for ignored_dir in ignore_list.get("directories", []):
        if ignored_dir in relative_path.parts:
            return True

    if file_path.suffix.lstrip(".") in ignore_list.get("extensions", []):
        return True

    return file_path.name in ignore_list.get("files", [])


def is_included(docs_list: dict, file_path: Path, repo_path: Path) -> bool:
    """Check if the directory or file should be included based on the docs list."""
    relative_path = file_path.relative_to(repo_path)

    for included_dir in docs_list.get("directories", []):
        if included_dir in relative_path.parts:
            return True

    if file_path.suffix.lstrip(".") in docs_list.get("extensions", []):
        return True

    return file_path.name in docs_list.get("files", [])
