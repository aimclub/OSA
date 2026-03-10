import os
import shutil
from fnmatch import fnmatch
from typing import List

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class RepoOrganizer:
    """
    Organizes repository by adding 'tests' and 'examples' directories if they aren't exist,
    moves Python test and example files into the appropriate folders.
    """

    # File patterns for Python test files only
    TEST_PATTERNS: List[str] = ["test_*.py", "*_test.py"]

    # File patterns for example files
    EXAMPLE_PATTERNS: List[str] = ["example*", "*example*", "*sample*", "*demo*"]

    def __init__(self, config_manager: ConfigManager) -> None:
        """
        Initialize with the local repository path.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
        """
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.tests_dir = os.path.join(self.repo_path, "tests")
        self.examples_dir = os.path.join(self.repo_path, "examples")

        self.events: list[OperationEvent] = []

    def organize(self) -> dict:
        """
        Ensure directories exist and move Python test and example files.
        """
        try:
            logger.info("Starting repository organization process.")
            self.add_directories()
            self.move_files_by_patterns(self.tests_dir, self.TEST_PATTERNS)
            self.move_files_by_patterns(self.examples_dir, self.EXAMPLE_PATTERNS)
            logger.info("Repository organization process completed.")

            return {
                "result": "Repository successfully organized",
                "events": self.events,
            }
        except Exception as e:
            logger.error(f"Unexpected failure during repository organization: {e}")
            self._emit(EventKind.FAILED, target="repo_organization", data={"error": repr(e)})
            return {
                "result": None,
                "events": self.events,
            }

    def add_directories(self) -> None:
        """
        Add 'tests' and 'examples' directories if they aren't exist.
        """
        for dir_path in (self.tests_dir, self.examples_dir):
            try:
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path)
                    logger.info(f"Created directory: {dir_path}")
                    self._emit(EventKind.CREATED, target=dir_path)
                else:
                    logger.info(f"Directory already exists: {dir_path}")
                    self._emit(EventKind.SKIPPED, target=dir_path, data={"reason": "already_exists"})
            except Exception as e:
                logger.error(f"Failed to create directory {dir_path}: {e}")
                self._emit(EventKind.FAILED, target=dir_path, data={"error": repr(e)})

    @staticmethod
    def match_patterns(filename: str, patterns: List[str]) -> bool:
        """
        Check if filename matches any of the provided patterns.

        Args:
            filename (str): Name of the file.
            patterns (List[str]): List of glob-like patterns.

        Returns:
            bool: True if file matches any pattern, False otherwise.
        """
        return any(fnmatch(filename.lower(), pattern.lower()) for pattern in patterns)

    def move_files_by_patterns(self, target_dir: str, patterns: List[str]) -> None:
        """
        Move files matching patterns to the target directory, excluding files already inside target_dir or its subdirectories.

        Args:
            target_dir: Directory to move files into.
            patterns: Patterns to match files.
        """
        excluded_dirs = {
            ".git",
            ".venv",
            "__pycache__",
            "node_modules",
            ".idea",
            ".vscode",
        }

        target_dir_abs = os.path.abspath(target_dir)

        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in excluded_dirs]

            for file in files:
                if self.match_patterns(file, patterns):
                    src = os.path.join(root, file)
                    src_abs = os.path.abspath(src)

                    if src_abs.startswith(target_dir_abs + os.sep):
                        continue

                    dst = os.path.join(target_dir, file)
                    try:
                        if src_abs != os.path.abspath(dst):
                            shutil.move(src, dst)
                            logger.info(f"Moved '{src}' to '{dst}'")
                            self._emit(EventKind.MOVED, target=file, data={"from": src, "to": dst})
                    except Exception as e:
                        logger.error(f"Failed to move '{src}' to '{dst}': {e}")
                        self._emit(EventKind.FAILED, target=file, data={"error": repr(e)})

    def _emit(self, kind: EventKind, target: str, data: dict | None = None):
        event = OperationEvent(kind=kind, target=target, data=data or {})
        self.events.append(event)
