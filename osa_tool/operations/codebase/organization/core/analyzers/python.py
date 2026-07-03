"""Python-specific import analyzer using AST."""

import ast
import re
from pathlib import Path
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
                    imports.update(self._resolve_import_from_node(file_path, node))
        except Exception:
            pass
        return imports

    def _resolve_import_from_node(self, file_path: str, node: ast.ImportFrom) -> Set[str]:
        imports = set()
        if node.level == 0:
            if node.module:
                imports.add(node.module)
            return imports

        package_parts = Path(file_path.replace("\\", "/")).with_suffix("").parts[:-1]
        parent_levels = max(node.level - 1, 0)
        base_parts = list(package_parts[: max(len(package_parts) - parent_levels, 0)])
        if node.module:
            imports.add(".".join(base_parts + node.module.split(".")))
            return imports

        for alias in node.names:
            if alias.name != "*":
                imports.add(".".join(base_parts + [alias.name]))
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

    def update_imports_in_content(
        self, file_path: str, content: str, old_import: str, new_import: str
    ) -> Optional[str]:
        """
        Update import statements in in-memory Python content.
        """
        updated = content

        def replace_from_import(match: re.Match[str]) -> str:
            imported_module = match.group("module")
            resolved = self._resolve_import_from_string(file_path, imported_module)
            if resolved != old_import:
                return match.group(0)
            replacement = self._format_import_for_file(file_path, imported_module, new_import)
            return f"from {replacement} import"

        from_pattern = r"from\s+(?P<module>[.\w]+)\s+import"
        updated = re.sub(from_pattern, replace_from_import, updated)
        import_pattern = rf"import\s+{re.escape(old_import)}(\s|$|,)"
        updated = re.sub(import_pattern, f"import {new_import}\\1", updated)
        return updated if updated != content else None

    def _resolve_import_from_string(self, file_path: str, import_value: str) -> str:
        if not import_value.startswith("."):
            return import_value

        dots = len(import_value) - len(import_value.lstrip("."))
        module = import_value[dots:]
        package_parts = Path(file_path.replace("\\", "/")).with_suffix("").parts[:-1]
        parent_levels = max(dots - 1, 0)
        base_parts = list(package_parts[: max(len(package_parts) - parent_levels, 0)])
        parts = base_parts + (module.split(".") if module else [])
        return ".".join(part for part in parts if part)

    def _format_import_for_file(self, file_path: str, existing_import: str, new_import: str) -> str:
        if not existing_import.startswith("."):
            return new_import

        package_parts = list(Path(file_path.replace("\\", "/")).with_suffix("").parts[:-1])
        target_parts = new_import.split(".")
        common = 0
        for current_part, target_part in zip(package_parts, target_parts):
            if current_part != target_part:
                break
            common += 1

        up_levels = len(package_parts) - common
        relative_prefix = "." * (up_levels + 1)
        suffix_parts = target_parts[common:]
        if suffix_parts:
            return f"{relative_prefix}{'.'.join(suffix_parts)}"
        return relative_prefix

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
