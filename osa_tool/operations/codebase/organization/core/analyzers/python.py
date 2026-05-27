"""Python-specific import analyzer using AST."""

import ast
import re
from typing import Set, Optional

from .base import BaseAnalyzer


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
        normalized = file_path.replace("\\", "/")
        for extension in self.file_extensions:
            if normalized.endswith(extension):
                normalized = normalized[: -len(extension)]
                break
        module_path = normalized.replace("/", ".")
        if module_path.endswith(".__init__"):
            module_path = module_path[: -len(".__init__")]
        return module_path

    def update_imports_in_content(self, file_path: str, content: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update import statements in in-memory Python content.
        """
        updated = content
        from_pattern = rf"from\s+{re.escape(old_import)}\s+import"
        updated = re.sub(from_pattern, f"from {new_import} import", updated)
        import_pattern = rf"import\s+{re.escape(old_import)}(\s|$|,)"
        updated = re.sub(import_pattern, f"import {new_import}\\1", updated)
        return updated if updated != content else None

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
            return self.update_imports_in_content(file_path, content, old_import, new_import)
        except Exception:
            return None
