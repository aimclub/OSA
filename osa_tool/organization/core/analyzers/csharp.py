"""C#-specific import analyzer for using statements."""

import re
from typing import Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class CSharpImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for C# files: extracts using statements.

    Handles C# source files, extracting and updating using directives,
    including aliased imports.
    """

    def __init__(self, base_path: str):
        """
        Initialize the C# import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".cs"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract using statements from a C# file.

        Handles both simple using directives and aliased imports.

        Args:
            file_path: Path to the C# file relative to base_path

        Returns:
            Set[str]: Set of imported namespaces
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            using_pattern = r"^\s*using\s+([^;]+);"
            for match in re.findall(using_pattern, content, re.MULTILINE):
                if "=" in match:
                    namespace = match.split("=")[1].strip()
                else:
                    namespace = match.strip()
                imports.add(namespace)
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Convert file path to namespace-style dotted path.

        Args:
            file_path: Path to the C# file relative to base_path

        Returns:
            str: Dotted namespace path
        """
        return file_path.replace(".cs", "").replace("/", ".").replace("\\", ".")

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update using statements in a C# file.

        Updates both simple using directives and aliased imports.

        Args:
            file_path: Path to the C# file relative to base_path
            old_import: Original namespace to replace
            new_import: New namespace to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            using_pattern = rf"^\s*using\s+{re.escape(old_import)};"
            content = re.sub(using_pattern, f"using {new_import};", content, flags=re.MULTILINE)
            alias_pattern = rf"^\s*using\s+[^=]+\s*=\s*{re.escape(old_import)};"

            def replace_alias(match):
                """
                Replace namespace in an aliased using directive.

                Args:
                    match: Regex match object containing the alias directive

                Returns:
                    str: Updated alias directive
                """
                return match.group(0).replace(old_import, new_import)

            content = re.sub(alias_pattern, replace_alias, content, flags=re.MULTILINE)
            content = re.sub(rf"\b{re.escape(old_import)}\b", new_import, content)
            return content
        except Exception:
            return None
