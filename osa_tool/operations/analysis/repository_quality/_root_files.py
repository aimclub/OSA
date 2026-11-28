"""Root filename rules shared by the local scorer and metadata assessment."""

import re
from collections.abc import Iterable
from typing import Literal

RootFileCheck = Literal["readme", "license_file", "dependency_manifest"]
_ROOT_FILE_RULES: tuple[tuple[RootFileCheck, re.Pattern[str]], ...] = (
    ("readme", re.compile(r"README(?:\.\w+)?", re.IGNORECASE)),
    ("license_file", re.compile(r"(?:LICENSE|LICENCE|COPYING|NOTICE)(?:\.\w+)?", re.IGNORECASE)),
    ("dependency_manifest", re.compile(r"requirements\.txt|pyproject\.toml", re.IGNORECASE)),
)
ROOT_FILE_CHECKS = tuple(check for check, _ in _ROOT_FILE_RULES)


def find_root_file(paths: Iterable[str], check: RootFileCheck) -> str | None:
    """Find the first root filename matching a repository-quality check.

    Args:
        paths: File paths relative to the repository root, in preferred order.
        check: The filename rule to apply.

    Returns:
        The original matching path, or None if no path matches.
    """
    pattern = next(pattern for name, pattern in _ROOT_FILE_RULES if name == check)
    return next((path for path in paths if pattern.fullmatch(path)), None)
