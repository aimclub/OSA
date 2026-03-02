"""Base analyzer class for all language-specific analyzers."""

import os
from pathlib import Path
from typing import Dict, List, Set, Tuple
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

from osa_tool.utils.logger import logger


class BaseAnalyzer:
    """
    Abstract base class for all language‑specific analyzers.

    This class provides a common interface and shared functionality for analyzing
    source code files in different programming languages. Subclasses must implement
    language-specific methods for discovering files, extracting imports, and
    updating import statements.

    Attributes:
        base_path (Path): Root directory path for analysis
        file_extensions (List[str]): List of file extensions this analyzer handles
        discovered_files (List[str]): List of discovered files relative to base_path
        import_map (Dict[str, Set[str]]): Mapping from module names to files that import them
    """

    def __init__(self, base_path: str):
        """
        Initialize the BaseAnalyzer with a base path.

        Args:
            base_path: Root directory path for analysis
        """
        self.base_path = Path(base_path)
        self.file_extensions: List[str] = []
        self.discovered_files: List[str] = []
        self.import_map: Dict[str, Set[str]] = {}

    def discover_files(self) -> List[str]:
        """
        Walk the base_path and collect all files with the configured extensions.
        Hidden directories (starting with '.') are skipped.

        Returns:
            List[str]: List of discovered file paths relative to base_path
        """
        self.discovered_files = []
        for ext in self.file_extensions:
            for path in self.base_path.rglob(f"*{ext}"):
                if path.is_file() and not any(part.startswith(".") for part in path.parts):
                    rel_path = str(path.relative_to(self.base_path))
                    self.discovered_files.append(rel_path)
        return self.discovered_files

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Return a set of imported module names found in the given file.

        Args:
            file_path: Path to the file relative to base_path

        Returns:
            Set[str]: Set of module names imported in the file

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def get_import_key(self, file_path: str) -> str:
        """
        Return a canonical key (e.g. dotted module path) for the file.

        Args:
            file_path: Path to the file relative to base_path

        Returns:
            str: Canonical import key for the file

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> str | None:
        """
        Return the updated content of the file with old_import replaced by new_import,
        or None if no changes were made.

        Args:
            file_path: Path to the file relative to base_path
            old_import: Original import string to replace
            new_import: New import string to use

        Returns:
            Optional[str]: Updated file content or None if no changes needed

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError

    def build_import_map(self):
        """
        Populate import_map: for each imported module, list of files that import it.
        Uses parallel processing with ThreadPoolExecutor for performance.
        """
        import_map = defaultdict(set)

        def process_file(fpath: str) -> Tuple[str, Set[str]]:
            """
            Process a single file to extract its imports.

            Args:
                fpath: File path relative to base_path

            Returns:
                Tuple[str, Set[str]]: File path and its imports
            """
            try:
                imports = self.extract_imports(fpath)
                return fpath, imports
            except Exception as e:
                logger.error(f"Error extracting imports from {fpath}: {e}")
                return fpath, set()

        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            future_to_file = {executor.submit(process_file, f): f for f in self.discovered_files}
            for future in as_completed(future_to_file):
                fpath, imports = future.result()
                for imp in imports:
                    import_map[imp].add(fpath)

        self.import_map = dict(import_map)

    def get_files_importing_module(self, module_path: str) -> Set[str]:
        """
        Return all files that import the given module.

        Args:
            module_path: Module path to look up

        Returns:
            Set[str]: Set of file paths that import the module
        """
        return self.import_map.get(module_path, set())
