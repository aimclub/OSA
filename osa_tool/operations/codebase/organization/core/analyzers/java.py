"""Java-specific import analyzer using regex."""

import re
from pathlib import Path
from typing import Set, Optional

from .base import BaseAnalyzer


class JavaImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for Java files: extracts import statements using regex.

    Handles Java source files and provides import extraction and update
    capabilities using regular expressions.
    """

    def __init__(self, base_path: str):
        """
        Initialize the Java import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".java"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract all import statements from a Java file using regex.

        Args:
            file_path: Path to the Java file relative to base_path

        Returns:
            Set[str]: Set of imported package names
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            import_pattern = r"^\s*import\s+(?:static\s+)?([^;]+);"
            for match in re.findall(import_pattern, content, re.MULTILINE):
                imports.add(match.strip())
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Convert a file path to a dotted package path.

        Args:
            file_path: Path to the Java file relative to base_path

        Returns:
            str: Dotted package path
        """
        full_path = self.base_path / file_path
        class_name = Path(file_path).stem
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            package_match = re.search(r"^\s*package\s+([^;]+);", content, re.MULTILINE)
            if package_match:
                return f"{package_match.group(1).strip()}.{class_name}"
        except Exception:
            pass

        normalized = file_path.replace("\\", "/")
        for prefix in ("src/main/java/", "src/test/java/", "src/java/"):
            if normalized.startswith(prefix):
                normalized = normalized[len(prefix) :]
                break
        return normalized.replace(".java", "").replace("/", ".")

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update import statements in a Java file by replacing old import with new one.

        Args:
            file_path: Path to the Java file relative to base_path
            old_import: Original import string to replace
            new_import: New import string to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            import_pattern = rf"^\s*import\s+(?:static\s+)?{re.escape(old_import)};"
            content = re.sub(import_pattern, f"import {new_import};", content, flags=re.MULTILINE)
            content = re.sub(rf"\b{re.escape(old_import)}\b", new_import, content)
            return content
        except Exception:
            return None
