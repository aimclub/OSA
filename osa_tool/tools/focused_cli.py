"""Shared helpers for focused, analysis-only command-line tools."""

from __future__ import annotations

import os

from osa_tool.utils.logger import setup_logging
from osa_tool.utils.utils import osa_project_root, parse_folder_name


def configure_focused_tool_logging(repository: str) -> None:
    """Configure logs for a focused tool that does not pass through ``osa_tool.run``."""
    logs_dir = os.path.join(os.path.dirname(osa_project_root()), "logs")
    setup_logging(parse_folder_name(repository), logs_dir)
