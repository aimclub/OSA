"""Python-specific import analyzer using AST."""

import ast
import re
from typing import Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class PythonImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for Python files using AST to extract import statements.

    Handles Python source files (.py, .pyx, .pxd, .pxi) and provides
    AST-based import extraction and update capabilities.
    """

    def __init__(self, base_path: str):
        """
        Initialize the Python import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".py", ".pyx", ".pxd", ".pxi"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract all import statements from a Python file using AST.

        Args:
            file_path: Path to the Python file relative to base_path

        Returns:
            Set[str]: Set of imported module names
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Convert a file path to a dotted module path for import lookups.

        Args:
            file_path: Path to the Python file relative to base_path

        Returns:
            str: Dotted module path (e.g., 'package.module')
        """
        return file_path.replace(".py", "").replace("/", ".").replace("\\", ".")

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update import statements in a Python file by replacing old import with new one.

        Args:
            file_path: Path to the Python file relative to base_path
            old_import: Original import string to replace
            new_import: New import string to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            from_pattern = rf"from\s+{re.escape(old_import)}\s+import"
            content = re.sub(from_pattern, f"from {new_import} import", content)
            import_pattern = rf"import\s+{re.escape(old_import)}(\s|$|,)"
            content = re.sub(import_pattern, f"import {new_import}\\1", content)
            return content
        except Exception:
            return None
