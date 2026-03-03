"""Ruby-specific import analyzer for require/load statements."""

import re
from typing import Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class RubyImportAnalyzer(BaseAnalyzer):
    """
    Analyzer for Ruby files: extracts require/load statements.

    Handles Ruby source files, extracting and updating require,
    require_relative, and load statements.
    """

    def __init__(self, base_path: str):
        """
        Initialize the Ruby import analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".rb", ".rake", ".gemspec"]

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract require/load statements from a Ruby file.

        Handles require, require_relative, and load statements.

        Args:
            file_path: Path to the Ruby file relative to base_path

        Returns:
            Set[str]: Set of required/loaded file paths
        """
        full_path = self.base_path / file_path
        imports = set()
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            require_pattern = r"^\s*(?:require|require_relative)\s+([^\n]+)"
            for match in re.findall(require_pattern, content, re.MULTILINE):
                match = re.sub(r"#.*", "", match).strip().strip("'\"")
                if match:
                    imports.add(match)
            load_pattern = r"^\s*load\s+([^\n]+)"
            for match in re.findall(load_pattern, content, re.MULTILINE):
                match = re.sub(r"#.*", "", match).strip().strip("'\"")
                if match:
                    imports.add(match)
        except Exception:
            pass
        return imports

    def get_import_key(self, file_path: str) -> str:
        """
        Get the import key for a Ruby file (path without extension).

        Args:
            file_path: Path to the Ruby file relative to base_path

        Returns:
            str: Path without extension
        """
        return file_path.replace(".rb", "").replace(".rake", "")

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update require/load statements in a Ruby file.

        Args:
            file_path: Path to the Ruby file relative to base_path
            old_import: Original require/load path to replace
            new_import: New require/load path to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            def replace_require(match):
                """
                Replace path in a require or load statement.

                Args:
                    match: Regex match object containing the require/load statement

                Returns:
                    str: Updated statement or original if no replacement needed
                """
                full_match = match.group(0)
                if re.search(rf'[\'"]{re.escape(old_import)}[\'"]', full_match):
                    return full_match.replace(old_import, new_import)
                return full_match

            require_pattern = r"^\s*(?:require|require_relative)\s+[^\n]+"
            content = re.sub(require_pattern, replace_require, content, flags=re.MULTILINE)
            load_pattern = r"^\s*load\s+[^\n]+"
            content = re.sub(load_pattern, replace_require, content, flags=re.MULTILINE)
            return content
        except Exception:
            return None
