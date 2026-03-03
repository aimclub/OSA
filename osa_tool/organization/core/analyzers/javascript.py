"""JavaScript/TypeScript-specific import analyzer using regex."""

import re
from typing import Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


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
                imports.add(match.strip())
            require_pattern = r'require\([\'"]([^\'"]+)[\'"]\)'
            for match in re.findall(require_pattern, content):
                imports.add(match.strip())
            dynamic_pattern = r'import\([\'"]([^\'"]+)[\'"]\)'
            for match in re.findall(dynamic_pattern, content):
                imports.add(match.strip())
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Get the import key for a JS/TS file (file path without extension).

        Args:
            file_path: Path to the JS/TS file relative to base_path

        Returns:
            str: Import key (path without extension)
        """
        return file_path.replace(".js", "").replace(".ts", "").replace(".jsx", "").replace(".tsx", "")

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
            content = re.sub(
                rf'import\s+(?:(?:[^;]+\s+from\s+)|(?:\*\s+as\s+[^;]+\s+from\s+)|(?:{{\s*[^}}]*\s*}}\s+from\s+))?[\'"]{re.escape(old_import)}[\'"]',
                lambda m: m.group(0).replace(old_import, new_import),
                content,
            )
            content = re.sub(rf'require\([\'"]{re.escape(old_import)}[\'"]\)', f"require('{new_import}')", content)
            content = re.sub(rf'import\([\'"]{re.escape(old_import)}[\'"]\)', f"import('{new_import}')", content)
            return content
        except Exception:
            return None
