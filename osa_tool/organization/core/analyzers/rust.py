"""Rust-specific import analyzer for use statements."""

import re
from typing import Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class RustImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for Rust files: extracts use statements.

    Handles Rust source files, extracting and updating use declarations.
    """

    def __init__(self, base_path: str):
        """
        Initialize the Rust import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".rs"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract use statements from a Rust file.

        Args:
            file_path: Path to the Rust file relative to base_path

        Returns:
            Set[str]: Set of imported module paths
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            use_pattern = r"^\s*use\s+([^;]+);"
            for match in re.findall(use_pattern, content, re.MULTILINE):
                module = re.split(r"::\{| as\s", match)[0].strip()
                if module:
                    imports.add(module)
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Convert file path to Rust module path notation.

        Args:
            file_path: Path to the Rust file relative to base_path

        Returns:
            str: Module path using :: separator
        """
        return file_path.replace(".rs", "").replace("/", "::").replace("\\", "::")

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update use statements in a Rust file.

        Args:
            file_path: Path to the Rust file relative to base_path
            old_import: Original import path to replace
            new_import: New import path to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            def replace_use(match):
                """
                Replace import path in a matched use statement.

                Args:
                    match: Regex match object containing the use statement

                Returns:
                    str: Updated use statement or original if no replacement needed
                """
                full_match = match.group(0)
                if re.search(rf"\b{re.escape(old_import)}\b", full_match):
                    return full_match.replace(old_import, new_import)
                return full_match

            use_pattern = r"^\s*use\s+[^;]+;"
            content = re.sub(use_pattern, replace_use, content, flags=re.MULTILINE)
            return content
        except Exception:
            return None
