"""JavaScript/TypeScript-specific import analyzer using regex."""

import os
from pathlib import Path
import re
from typing import Set, Optional

from .base import BaseAnalyzer


class JavaScriptImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for JavaScript/TypeScript files: extracts import/require/dynamic import.

    Handles JS/TS files and extracts all types of import statements including
    ES6 imports, CommonJS require, and dynamic imports.
    """

    def __init__(self, base_path: str):
        """
        Initialize the JavaScript/TypeScript import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract all import statements from a JS/TS file using regex.

        Handles ES6 imports, CommonJS require, and dynamic import() expressions.

        Args:
            file_path: Path to the JS/TS file relative to base_path

        Returns:
            Set[str]: Set of imported module paths
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            import_pattern = r'import\s+(?:(?:[^;]+\s+from\s+)|(?:\*\s+as\s+[^;]+\s+from\s+)|(?:{[^}]+}\s+from\s+))?[\'"]([^\'"]+)[\'"]'
            for match in re.findall(import_pattern, content):
                imports.add(self._canonicalize_import(file_path, match.strip()))
            require_pattern = r'require\([\'"]([^\'"]+)[\'"]\)'
            for match in re.findall(require_pattern, content):
                imports.add(self._canonicalize_import(file_path, match.strip()))
            dynamic_pattern = r'import\([\'"]([^\'"]+)[\'"]\)'
            for match in re.findall(dynamic_pattern, content):
                imports.add(self._canonicalize_import(file_path, match.strip()))
        except Exception:
            pass
        return {imp for imp in imports if imp}

    def get_import_key(self, file_path: str) -> str:
        """
        Get the import key for a JS/TS file (file path without extension).

        Args:
            file_path: Path to the JS/TS file relative to base_path

        Returns:
            str: Import key (path without extension)
        """
        normalized = file_path.replace("\\", "/")
        for ext in self.file_extensions:
            if normalized.endswith(ext):
                normalized = normalized[: -len(ext)]
                break
        if normalized.endswith("/index"):
            return normalized[: -len("/index")]
        return normalized

    def _canonicalize_import(self, file_path: str, import_path: str) -> str:
        if not import_path.startswith("."):
            return import_path

        importer_dir = Path(file_path.replace("\\", "/")).parent.as_posix()
        normalized = os.path.normpath(os.path.join(importer_dir, import_path)).replace("\\", "/")
        return self.get_import_key(normalized)

    def _to_relative_import(self, file_path: str, target_import: str) -> str:
        importer_dir = Path(file_path.replace("\\", "/")).parent
        target_path = Path(target_import.replace("\\", "/"))
        relative = Path(os.path.relpath(target_path, importer_dir)).as_posix()
        if not relative.startswith("."):
            relative = f"./{relative}"
        return relative

    def _preserve_import_style(self, original_specifier: str, new_specifier: str) -> str:
        if not original_specifier.startswith("."):
            return new_specifier

        original_path = original_specifier.replace("\\", "/")
        original_suffixes = Path(original_path).suffixes
        if original_suffixes:
            joined_suffix = "".join(original_suffixes)
            if not new_specifier.endswith(joined_suffix):
                return f"{new_specifier}{joined_suffix}"

        if original_path.endswith("/index") and not new_specifier.endswith("/index"):
            return f"{new_specifier}/index"
        return new_specifier

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update import statements in a JS/TS file.

        Updates ES6 imports, require() calls, and dynamic import() expressions.

        Args:
            file_path: Path to the JS/TS file relative to base_path
            old_import: Original import string to replace
            new_import: New import string to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            def replace_match(match: re.Match[str]) -> str:
                specifier = match.group("spec")
                if self._canonicalize_import(file_path, specifier) != old_import:
                    return match.group(0)
                if specifier.startswith("."):
                    replacement = self._to_relative_import(file_path, new_import)
                    replacement = self._preserve_import_style(specifier, replacement)
                else:
                    replacement = new_import
                return match.group(0).replace(specifier, replacement)

            patterns = [
                r'(?P<stmt>import\s+(?:(?:[^;]+\s+from\s+)|(?:\*\s+as\s+[^;]+\s+from\s+)|(?:{[^}]+}\s+from\s+))(?P<quote>[\'"])(?P<spec>[^\'"]+)(?P=quote))',
                r'(?P<stmt>require\((?P<quote>[\'"])(?P<spec>[^\'"]+)(?P=quote)\))',
                r'(?P<stmt>import\((?P<quote>[\'"])(?P<spec>[^\'"]+)(?P=quote)\))',
            ]
            for pattern in patterns:
                content = re.sub(pattern, replace_match, content)
            return content
        except Exception:
            return None
