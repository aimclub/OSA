"""Executor for filesystem actions during reorganization."""

import os
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from osa_tool.utils.logger import logger
from osa_tool.organization.core.analyzers.base import BaseAnalyzer
from osa_tool.organization.core.executor.batch_updater import BatchImportUpdater


class ActionExecutor:
    """
    Executes filesystem actions (move, copy, delete, create) and records moves
    so that imports can be updated later.

    Handles safe execution of reorganization actions with proper error handling
    and move tracking for import updates.
    """

    def __init__(self, base_path: Path, analyzers: Dict[str, BaseAnalyzer]):
        """
        Initialize the action executor.

        Args:
            base_path: Root directory path
            analyzers: Dictionary of language analyzers for import tracking
        """
        self.base_path = base_path
        self.analyzers = analyzers
        self.moves: List[Tuple[str, str]] = []

    def execute_all(self, actions: List[dict]):
        """
        Execute all actions in the provided list.

        First processes individual moves and then handles batch import updates.

        Args:
            actions: List of action dictionaries to execute
        """
        for action in actions:
            if action["type"] in ("move_file", "rename_file"):
                src = action.get("source") or action["old_path"]
                dst = action.get("destination") or action["new_path"]
                self._move_file(src, dst)
            else:
                self._execute_single(action)

        if self.moves:
            updater = BatchImportUpdater(self.base_path, self.analyzers)
            for old, new in self.moves:
                updater.add_move(old, new)
            updater.apply_all()
        self.moves.clear()

    def _execute_single(self, action: dict):
        """
        Execute a single non-move action.

        Args:
            action: Action dictionary to execute
        """
        typ = action["type"]
        if typ == "create_directory":
            self._create_directory(action["path"])
        elif typ == "create_file":
            self._create_file(action["path"], action.get("content", ""))
        elif typ == "move_directory":
            self._move_directory(action["source"], action["destination"])
        elif typ == "move_files":
            pattern = action["source_pattern"]
            dest_dir = action["destination_dir"]
            self._move_files(pattern, dest_dir, action.get("reason", ""))
        elif typ == "delete_file":
            self._delete_file(action["path"])
        elif typ == "delete_directory":
            self._delete_directory(action["path"])
        else:
            logger.warning(f"Unknown action type: {typ}")

    def _create_directory(self, path: str):
        """
        Create a directory and any necessary parent directories.

        Args:
            path: Directory path relative to base_path
        """
        full = self.base_path / path
        if not full.exists():
            full.mkdir(parents=True, exist_ok=True)

    def _create_file(self, path: str, content: str):
        """
        Create a file with the specified content.

        Args:
            path: File path relative to base_path
            content: File content to write
        """
        full = self.base_path / path
        if full.exists():
            logger.warning("File already exists: %s", path)
            return
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")

    def _move_file(self, source: str, destination: str):
        """
        Move a single file and record the move for import updates.

        Args:
            source: Source file path relative to base_path
            destination: Destination file path relative to base_path
        """
        src = self.base_path / source
        dst = self.base_path / destination

        if not src.exists():
            logger.warning(f"Source file does not exist: {source}")
            return

        if dst.exists():
            logger.warning(f"Destination file already exists: {destination}")
            return

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        src.unlink()

        self.moves.append((source, destination))

    def _move_directory(self, source: str, destination: str):
        """
        Move a directory and record all contained files for import updates.

        Args:
            source: Source directory path relative to base_path
            destination: Destination directory path relative to base_path
        """
        src = self.base_path / source
        dst = self.base_path / destination

        if not src.exists() or not src.is_dir():
            logger.warning(f"Source directory does not exist or is not a directory: {source}")
            return

        if dst.exists():
            logger.warning(f"Destination directory already exists: {destination}")
            return

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

        for root, _, files in os.walk(dst):
            for file in files:
                full_file = Path(root) / file
                new_rel = str(full_file.relative_to(self.base_path))
                sub_path = full_file.relative_to(dst)
                old_rel = str((src / sub_path).relative_to(self.base_path))
                self.moves.append((old_rel, new_rel))

    def _move_files(self, source_pattern: str, destination_dir: str, reason: str = ""):
        """
        Move multiple files matching a pattern to a destination directory.

        Args:
            source_pattern: Glob pattern for source files
            destination_dir: Destination directory path relative to base_path
            reason: Optional reason for the move
        """
        full_dest = self.base_path / destination_dir
        matched = list(self.base_path.glob(source_pattern))
        if not matched:
            logger.warning(f"No files match pattern '{source_pattern}'")
            return

        for src_path in matched:
            if not src_path.is_file():
                continue
            rel_src = str(src_path.relative_to(self.base_path))
            dest_path = full_dest / src_path.name
            rel_dest = str(dest_path.relative_to(self.base_path))
            self._move_file(rel_src, rel_dest)

    def _delete_file(self, path: str):
        """
        Delete a single file.

        Args:
            path: File path relative to base_path
        """
        full = self.base_path / path
        if full.exists():
            full.unlink()

    def _delete_directory(self, path: str):
        """
        Delete a directory only if it's empty.

        Args:
            path: Directory path relative to base_path
        """
        full = self.base_path / path
        if not full.exists():
            logger.warning(f"Directory does not exist: {path}")
            return

        if not full.is_dir():
            logger.warning(f"Path is not a directory: {path}")
            return

        if any(full.iterdir()):
            logger.warning(f"Directory {path} is not empty, skipping deletion")
            return

        full.rmdir()
        logger.debug(f"Deleted empty directory: {path}")
