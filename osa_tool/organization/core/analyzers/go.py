"""Go-specific import analyzer using go list command."""

import os
import json
import re
import subprocess
from typing import List, Set, Optional

from osa_tool.organization.core.analyzers.base import BaseAnalyzer
from osa_tool.utils.logger import logger


class GoPackagesAnalyzer(BaseAnalyzer):
    """
    Analyzer for Go that uses `go list -json` to get accurate package info.

    Runs `go list` once and caches results for efficient import analysis.
    Provides accurate package information using Go's own tooling.
    """

    def __init__(self, base_path: str):
        """
        Initialize the Go packages analyzer.

        Args:
            base_path: Root directory path for analysis
        """
        super().__init__(base_path)
        self.file_extensions = [".go"]
        self._package_cache = None

    def _load_package_cache(self):
        """
        Load package information using `go list -json` and cache it.

        Runs `go list` to get package information for all Go packages in the project.
        Results are cached in _package_cache mapping file paths to package info.
        """
        if self._package_cache is not None:
            return
        self._package_cache = {}
        try:
            result = subprocess.run(
                ["go", "list", "-json", "./..."], cwd=self.base_path, capture_output=True, text=True, check=True
            )
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    pkg = json.loads(line)
                except json.JSONDecodeError:
                    continue
                import_path = pkg.get("ImportPath", "")
                imports = set(pkg.get("Imports", []))
                for go_file in pkg.get("GoFiles", []):
                    full_path = os.path.join(pkg["Dir"], go_file)
                    rel = os.path.relpath(full_path, self.base_path)
                    self._package_cache[rel] = (import_path, imports)
                for extra in ("CgoFiles", "TestGoFiles", "XTestGoFiles"):
                    for go_file in pkg.get(extra, []):
                        full_path = os.path.join(pkg["Dir"], go_file)
                        rel = os.path.relpath(full_path, self.base_path)
                        self._package_cache[rel] = (import_path, imports)
        except Exception as e:
            logger.error(f"Go list failed: {e}")
            self._package_cache = {}

    def discover_files(self) -> List[str]:
        """
        Discover Go files by loading the package cache first.

        Returns:
            List[str]: List of discovered Go file paths
        """
        self._load_package_cache()
        self.discovered_files = list(self._package_cache.keys())
        return self.discovered_files

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract imports for a Go file from the package cache.

        Args:
            file_path: Path to the Go file relative to base_path

        Returns:
            Set[str]: Set of imported package paths
        """
        info = self._package_cache.get(file_path)
        if info:
            return info[1]
        return set()

    def get_import_key(self, file_path: str) -> str:
        """
        Get the import key (package import path) for a Go file.

        Args:
            file_path: Path to the Go file relative to base_path

        Returns:
            str: Package import path
        """
        info = self._package_cache.get(file_path)
        if info:
            return info[0]
        return file_path.replace(".go", "")

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update import statements in a Go file.

        Updates both grouped imports (import ( ... )) and single import lines.

        Args:
            file_path: Path to the Go file relative to base_path
            old_import: Original import path to replace
            new_import: New import path to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()

            def replace_in_block(match):
                """
                Replace import paths within a grouped import block.

                Args:
                    match: Regex match object containing the import block

                Returns:
                    str: Updated import block
                """
                block = match.group(1)
                lines = block.split("\n")
                updated = []
                for line in lines:
                    if f'"{old_import}"' in line:
                        line = line.replace(f'"{old_import}"', f'"{new_import}"')
                    updated.append(line)
                return "import (\n" + "\n".join(updated) + "\n)"

            content = re.sub(r"import\s*\((.*?)\)", replace_in_block, content, flags=re.DOTALL)
            content = re.sub(rf'import\s+"{re.escape(old_import)}"', f'import "{new_import}"', content)
            return content
        except Exception:
            return None
