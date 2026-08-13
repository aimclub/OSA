"""Lazy loaders for graph-based repository-validation operations."""

from __future__ import annotations

import importlib
from typing import Any

_INSTALL_MESSAGE = (
    "Repository validation requires the repository-validation extra. "
    'Install it with: pip install "osa_tool[repository-validation]".'
)


def _load_validator(module_name: str, class_name: str) -> type[Any]:
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError(_INSTALL_MESSAGE) from exc
    return getattr(module, class_name)


def load_doc_validator() -> type[Any]:
    """Load the document validator only when its optional graph stack is needed."""
    return _load_validator("osa_tool.operations.analysis.repository_validation.doc_validator", "DocValidator")


def load_paper_validator() -> type[Any]:
    """Load the paper validator only when its optional graph stack is needed."""
    return _load_validator("osa_tool.operations.analysis.repository_validation.paper_validator", "PaperValidator")
