"""Batch import updater for handling multiple file moves."""

from pathlib import Path
from typing import Dict, List, Tuple
from collections import defaultdict

from osa_tool.utils.logger import logger
from osa_tool.organization.core.utils import atomic_write_file
from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class BatchImportUpdater:
    """
    Handles batch updating of imports after multiple file moves.

    Resolves moved files to their final destinations and updates all importing files
    with the new import paths. Maintains a mapping of moves and applies updates
    intelligently to avoid conflicts.
    """

    def __init__(self, base_path: Path, analyzers: Dict[str, BaseAnalyzer]):
        """
        Initialize the batch import updater.

        Args:
            base_path: Root directory path
            analyzers: Dictionary mapping language names to analyzer instances
        """
        self.base_path = base_path
        self.analyzers = analyzers
        self.moves: List[Tuple[str, str]] = []

    def add_move(self, old_path: str, new_path: str):
        """
        Record a file move operation.

        Args:
            old_path: Original file path relative to base_path
            new_path: New file path relative to base_path
        """
        self.moves.append((old_path, new_path))

    def apply_all(self):
        """
        Apply all recorded moves to update import statements.

        Resolves all import dependencies and updates files that import moved
        modules with the new import paths.
        """
        if not self.moves:
            return

        file_key_mapping = defaultdict(dict)
        for old_path, new_path in self.moves:
            for lang, analyzer in self.analyzers.items():
                if analyzer.file_extensions and any(old_path.endswith(ext) for ext in analyzer.file_extensions):
                    old_key = analyzer.get_import_key(old_path)
                    new_key = analyzer.get_import_key(new_path)
                    file_key_mapping[old_path][lang] = (old_key, new_key)
                    break

        updates_needed = defaultdict(list)

        for old_path, key_mapping in file_key_mapping.items():
            for lang, (old_key, new_key) in key_mapping.items():
                analyzer = self.analyzers[lang]
                importing_files = analyzer.get_files_importing_module(old_key)
                for target in importing_files:
                    resolved_target = self._resolve_path(target, self.moves)
                    updates_needed[resolved_target].append((old_key, new_key, lang))

        for target_file, replacements in updates_needed.items():
            content = None
            full_path = self.base_path / target_file
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Failed to read {target_file}: {e}")
                continue

            changed = False
            for old_key, new_key, lang in replacements:
                analyzer = self.analyzers[lang]
                new_content = analyzer.update_imports_in_file(target_file, old_key, new_key)
                if new_content is not None:
                    content = new_content
                    changed = True

            if changed:
                atomic_write_file(full_path, content)
                logger.debug(f"Updated imports in {target_file}")

    @staticmethod
    def _resolve_path(path: str, moves: List[Tuple[str, str]]) -> str:
        """
        Resolve a path through multiple moves to its final destination.

        Args:
            path: Original path to resolve
            moves: List of (old_path, new_path) move operations

        Returns:
            str: Final resolved path after all moves
        """
        moves_dict = dict(moves)
        visited = set()
        while path in moves_dict and path not in visited:
            visited.add(path)
            path = moves_dict[path]
        return path
