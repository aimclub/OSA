"""Generic reference analyzer for text files."""

import os
import re
from pathlib import Path
from typing import Set, Optional, List

from osa_tool.organization.core.analyzers.base import BaseAnalyzer


class GenericReferenceAnalyzer(BaseAnalyzer):
    """
    Analyzer that detects references to files/directories in any text file
    not handled by language‑specific analyzers.

    Looks for quoted strings or unquoted path‑like tokens that actually exist
    in the repository. Handles any text file type and provides basic reference
    detection and updating capabilities.
    """

    def __init__(self, base_path: str, excluded_extensions: Set[str] = None):
        """
        Initialize the generic reference analyzer.

        Args:
            base_path: Root directory path for analysis
            excluded_extensions: Set of file extensions to exclude from analysis
        """
        super().__init__(base_path)
        self.excluded_extensions = excluded_extensions or set()
        self.binary_extensions = {
            ".exe",
            ".dll",
            ".so",
            ".dylib",
            ".bin",
            ".obj",
            ".o",
            ".a",
            ".lib",
            ".pyc",
            ".class",
            ".jar",
            ".war",
            ".ear",
            ".zip",
            ".tar",
            ".gz",
            ".bz2",
            ".7z",
            ".rar",
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".ico",
            ".svg",
            ".pdf",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".ppt",
            ".pptx",
            ".mp3",
            ".mp4",
            ".avi",
            ".mov",
            ".mkv",
            ".webm",
            ".iso",
        }

    def discover_files(self) -> List[str]:
        """
        Discover all text files not handled by language-specific analyzers.

        Walks the directory tree, excluding binary files and files with
        extensions handled by other analyzers.

        Returns:
            List[str]: List of discovered text file paths
        """
        self.discovered_files = []
        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in self.excluded_extensions:
                    continue
                if ext in self.binary_extensions:
                    continue
                full_path = Path(root) / file
                if not self._is_text_file(full_path):
                    continue
                rel_path = str(full_path.relative_to(self.base_path))
                self.discovered_files.append(rel_path)
        return self.discovered_files

    @staticmethod
    def _is_text_file(path: Path) -> bool:
        """
        Check if a file appears to be a text file (not binary).

        Reads the first 1024 bytes and checks for null bytes and printable
        character ratio.

        Args:
            path: Path to the file to check

        Returns:
            bool: True if the file appears to be text, False otherwise
        """
        try:
            with open(path, "rb") as f:
                chunk = f.read(1024)
            if b"\x00" in chunk:
                return False
            printable = set(bytes(range(32, 127)) + b"\n\r\t\f")
            non_printable = sum(1 for b in chunk if b not in printable)
            return non_printable < len(chunk) * 0.3
        except Exception:
            return False

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extract references to existing files/directories from a text file.

        Looks for quoted strings and unquoted path-like tokens that correspond
        to actual files/directories in the repository.

        Args:
            file_path: Path to the text file relative to base_path

        Returns:
            Set[str]: Set of referenced file/directory paths
        """
        full_path = self.base_path / file_path
        references = set()
        try:
            content = full_path.read_text(encoding="utf-8", errors="ignore")
            quoted_patterns = [
                r'"([^"]+)"',
                r"'([^']+)'",
                r"`([^`]+)`",
            ]
            candidates = []
            for pat in quoted_patterns:
                candidates.extend(re.findall(pat, content))

            unquoted = re.findall(r'(?:^|\s)([./\\][^\s<>:|?"*]+)(?=\s|$)', content)
            candidates.extend(unquoted)

            for cand in candidates:
                norm = cand.replace("\\", "/")
                norm = re.sub(r"^\./", "", norm)
                if re.match(r"^(https?|ftp|git|ssh)://", norm, re.I):
                    continue
                if norm.startswith(("/", "\\")):
                    continue
                candidate_path = self.base_path / norm
                if candidate_path.exists():
                    references.add(norm)
                elif (self.base_path / cand).exists():
                    references.add(cand)
        except Exception:
            pass
        return references

    def get_import_key(self, file_path: str) -> str:
        """
        Get the import key for a text file (the file path itself).

        Args:
            file_path: Path to the text file relative to base_path

        Returns:
            str: The file path as import key
        """
        return file_path

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> Optional[str]:
        """
        Update references in a text file by replacing old path with new one.

        Args:
            file_path: Path to the text file relative to base_path
            old_import: Original path to replace
            new_import: New path to use

        Returns:
            Optional[str]: Updated file content or None if update failed
        """
        full_path = self.base_path / file_path
        try:
            content = full_path.read_text(encoding="utf-8")
            boundary = r'(?<=^|\s|["\'`([{])'
            end_boundary = r'(?=$|\s|["\'`)\]}]|,|;)'
            pattern = boundary + re.escape(old_import) + end_boundary
            new_content, count = re.subn(pattern, new_import, content)
            return new_content if count > 0 else None
        except Exception:
            return None
