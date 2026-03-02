"""Kotlin-specific import analyzer."""

import re
from typing import Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class KotlinImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for Kotlin files: extracts import statements.

    Handles Kotlin source files, extracting and updating import declarations.
    """

    def __init__(self, base_path: str):
        """
        Initialize the Kotlin import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".kt", ".kts"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract import statements from a Kotlin file.

        Args:
            file_path: Path to the Kotlin file relative to base_path

        Returns:
            Set[str]: Set of imported package/class names
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            import_pattern = r"^\s*import\s+([^\n]+)"
            for match in re.findall(import_pattern, content, re.MULTILINE):
                match = re.sub(r"//.*", "", match).strip()
                if match:
                    imports.add(match)
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Convert file path to dotted package path.

        Args:
            file_path: Path to the Kotlin file relative to base_path

        Returns:
            str: Dotted package path
        """
        return file_path.replace(".kt", "").replace(".kts", "").replace("/", ".").replace("\\", ".")

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update import statements in a Kotlin file.

        Args:
            file_path: Path to the Kotlin file relative to base_path
            old_import: Original import to replace
            new_import: New import to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            content = re.sub(
                rf"^\s*import\s+{re.escape(old_import)}(\s|$)", f"import {new_import}\\1", content, flags=re.MULTILINE
            )
            content = re.sub(rf"\b{re.escape(old_import)}\b", new_import, content)
            return content
        except Exception:
            return None
