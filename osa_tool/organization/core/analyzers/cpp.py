"""C/C++-specific import analyzer for #include directives."""

import re
from typing import Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class CppImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for C/C++ files: extracts #include directives.

    Handles C and C++ source and header files, extracting and updating
    #include directives.
    """

    def __init__(self, base_path: str):
        """
        Initialize the C/C++ import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".c", ".cpp", ".cc", ".cxx", ".h", ".hpp", ".hh", ".hxx"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract all #include directives from a C/C++ file.

        Args:
            file_path: Path to the C/C++ file relative to base_path

        Returns:
            Set[str]: Set of included file paths
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            include_pattern = r'^\s*#include\s+[<"]([^>"]+)[>"]'
            for match in re.findall(include_pattern, content, re.MULTILINE):
                imports.add(match.strip())
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Get the import key for a C/C++ file (the file path itself).

        Args:
            file_path: Path to the C/C++ file relative to base_path

        Returns:
            str: The file path as import key
        """
        return file_path

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update #include directives in a C/C++ file.

        Args:
            file_path: Path to the C/C++ file relative to base_path
            old_import: Original include path to replace
            new_import: New include path to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            def replace_include(match):
                """
                Replace include path in a matched #include directive.

                Args:
                    match: Regex match object containing the include directive

                Returns:
                    str: Updated include directive or original if no replacement needed
                """
                prefix = match.group(1)
                old_path = match.group(2)
                suffix = match.group(3)
                if old_path == old_import:
                    return f"{prefix}{new_import}{suffix}"
                return match.group(0)

            include_pattern = r'^(\s*#include\s+[<"])([^>"]+)([>"])'
            content = re.sub(include_pattern, replace_include, content, flags=re.MULTILINE)
            return content
        except Exception:
            return None
