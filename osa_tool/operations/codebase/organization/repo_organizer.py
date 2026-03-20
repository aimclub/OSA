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
        Initialize the RepoOrganizer with configuration-derived repository paths.
        
        WHY: This constructor sets up essential local paths based on the provided configuration, enabling the organizer to locate and operate on the repository's directory structure, tests, and examples folders.
        
        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences. Specifically, its Git settings are used to determine the repository URL and derive the local folder name.
        
        Initializes the following instance attributes:
        - repo_url: The remote repository URL extracted from the configuration.
        - repo_path: The absolute local path to the repository, constructed by joining the current working directory with the parsed folder name from the repo_url.
        - tests_dir: The absolute path to the 'tests' directory within the local repository.
        - examples_dir: The absolute path to the 'examples' directory within the local repository.
        - events: An empty list to store operation events.
        """
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.tests_dir = os.path.join(self.repo_path, "tests")
        self.examples_dir = os.path.join(self.repo_path, "examples")

        self.events: list[OperationEvent] = []

    def organize(self) -> dict:
        """
        Ensure directories exist and move Python test and example files.
        
        This method orchestrates the repository organization process by first creating standard directories (if missing) and then relocating test and example files into them based on predefined filename patterns. It logs each step and emits events for tracking and auditing purposes.
        
        Why:
        - To standardize the repository structure by grouping related files (tests, examples) into dedicated directories, improving project organization and accessibility.
        - To provide a clear audit trail of the organization process through logging and event emission, which aids in debugging and reporting.
        
        Args:
            self: The RepoOrganizer instance.
        
        Returns:
            A dictionary containing:
                - "result": A success message string if organization succeeded, or None if an exception occurred.
                - "events": The list of events recorded during the organization process (including any failures).
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
        Add 'tests' and 'examples' directories if they do not already exist.
        
        This method ensures the repository contains standard directories for tests and examples by creating them when missing. It logs each creation, skip, or failure event and emits corresponding events for tracking and auditing purposes.
        
        Why:
        - To standardize repository structure by including common directories that improve project organization and accessibility.
        - To provide clear logging and event emission for monitoring the outcome of directory creation attempts.
        
        Args:
            self.tests_dir: The path where the 'tests' directory should be located.
            self.examples_dir: The path where the 'examples' directory should be located.
        
        Note:
            If a directory already exists, the method logs this and emits a SKIPPED event. If creation fails, it logs an error and emits a FAILED event with error details.
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
        Check if filename matches any of the provided glob-like patterns.
        
        Args:
            filename: Name of the file.
            patterns: List of glob-like patterns (e.g., "*.py", "docs/*.md").
        
        Returns:
            True if the filename matches any pattern, False otherwise.
        
        Why:
            This method performs case-insensitive matching to ensure consistent behavior across different operating systems where file systems may be case-sensitive or case-insensitive. Lowercasing both the filename and the pattern avoids mismatches due to case differences.
        """
        return any(fnmatch(filename.lower(), pattern.lower()) for pattern in patterns)

    def move_files_by_patterns(self, target_dir: str, patterns: List[str]) -> None:
        """
        Move files matching patterns to the target directory, excluding files already inside target_dir or its subdirectories.
        
        Args:
            target_dir: Directory to move files into.
            patterns: Glob-like patterns to match filenames (e.g., "*.py", "docs/*.md").
        
        Why:
            This method organizes repository files by relocating them based on pattern matching, which helps in structuring the project. It automatically skips common development directories (like .git, node_modules) to avoid moving version control or dependency files. Files already located within the target directory or its subdirectories are excluded to prevent unnecessary moves.
        
        Note:
            The operation logs each move and emits events for tracking. If a move fails, an error is logged and a failure event is emitted.
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
        """
        Emit an operation event and store it in the events list.
        
        This method is used internally to record significant actions (like file creation, deletion, or modification) performed by the RepoOrganizer. Tracking these events allows the tool to log operations, support rollback capabilities, and generate summaries of changes made during repository enhancement.
        
        Args:
            kind: The type of event (e.g., create, delete, modify).
            target: The target of the event, typically a file or directory path.
            data: Optional dictionary containing additional event-specific details, such as content changes or metadata.
        
        Returns:
            None.
        """
        event = OperationEvent(kind=kind, target=target, data=data or {})
        self.events.append(event)
