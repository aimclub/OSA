import fnmatch
import os
from osa_tool.docs_generator.repoagent.settings import SettingsManager

class GitignoreChecker:
    """GitignoreChecker is a utility class for checking files and folders against a .gitignore file to determine which should be ignored.

This class is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It integrates various functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories. The tool also includes a chat engine and a multi-task dispatch system to enhance user interaction and process management. Additionally, it provides utilities for handling .gitignore files and managing fake files for untracked and modified content.

Args:
    directory (str): The directory to check for ignored files and folders.
    gitignore_path (str): The path to the .gitignore file. If the file is not found at the specified path, a default path is used.

Returns:
    list: A list of files and folders that are not ignored according to the .gitignore file.

Raises:
    FileNotFoundError: If the .gitignore file is not found at the specified path and the default path.

Note:
    The class reads the .gitignore file, parses it, and checks files and folders in the specified directory against the patterns defined in the file.

---

_init_(self, directory: str, gitignore_path: str)
Initializes the GitignoreChecker with the specified directory and .gitignore file path.

Args:
    directory (str): The directory to check for ignored files and folders.
    gitignore_path (str): The path to the .gitignore file.

---

_load_gitignore_patterns(self) -> tuple
Loads and parses the .gitignore file to extract folder and file patterns.

Returns:
    tuple: A tuple containing two lists: folder_patterns and file_patterns.

Raises:
    FileNotFoundError: If the .gitignore file is not found at the specified path and the default path.

---

_parse_gitignore(gitignore_content: str) -> list
Parses the content of the .gitignore file to extract valid patterns.

Args:
    gitignore_content (str): The content of the .gitignore file.

Returns:
    list: A list of valid .gitignore patterns.

---

_split_gitignore_patterns(gitignore_patterns: list) -> tuple
Splits the .gitignore patterns into folder and file patterns.

Args:
    gitignore_patterns (list): A list of .gitignore patterns.

Returns:
    tuple: A tuple containing two lists: folder_patterns and file_patterns.

---

_is_ignored(path: str, patterns: list, is_dir: bool=False) -> bool
Checks if a given path is ignored based on the .gitignore patterns.

Args:
    path (str): The path to check.
    patterns (list): The list of .gitignore patterns.
    is_dir (bool, optional): Whether the path is a directory. Defaults to False.

Returns:
    bool: True if the path is ignored, False otherwise.

---

check_files_and_folders(self) -> list
Checks all files and folders in the specified directory against the .gitignore patterns and returns a list of not ignored files.

Returns:
    list: A list of files and folders that are not ignored according to the .gitignore file."""

    def __init__(self, directory: str, gitignore_path: str):
        """Initializes the GitignoreChecker object.

Sets the directory and gitignore path, and loads the folder and file patterns from the gitignore file.

Args:
    directory (str): The directory to be checked against the gitignore file.
    gitignore_path (str): The path to the .gitignore file.

Returns:
    None

Raises:
    FileNotFoundError: If the gitignore file at the specified path does not exist.

Note:
    This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It ensures that the .gitignore file is correctly loaded to manage file operations and untracked content."""
        self.directory = directory
        self.gitignore_path = gitignore_path
        self.folder_patterns, self.file_patterns = self._load_gitignore_patterns()

    def _load_gitignore_patterns(self) -> tuple:
        """Loads and processes the .gitignore file patterns.

This method attempts to open and read the content of the .gitignore file specified by `self.gitignore_path`. If the file is not found, it falls back to a default .gitignore file located in the root of the project. The content is then parsed to extract valid patterns, which are split into folder and file patterns.

Args:
    self: The instance of the GitignoreChecker class.

Returns:
    tuple: A tuple containing two lists, the first for folder patterns and the second for file patterns.

Raises:
    None

Note:
    This method is used internally by the GitignoreChecker class to load and process the .gitignore file. It relies on the `_parse_gitignore` and `_split_gitignore_patterns` methods for parsing and splitting the patterns, respectively. The tool is part of a comprehensive system designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate."""
        try:
            with open(self.gitignore_path, 'r', encoding='utf-8') as file:
                gitignore_content = file.read()
        except FileNotFoundError:
            default_path = os.path.join(os.path.dirname(__file__), '..', '..', '.gitignore')
            with open(default_path, 'r', encoding='utf-8') as file:
                gitignore_content = file.read()
        patterns = self._parse_gitignore(gitignore_content)
        return self._split_gitignore_patterns(patterns)

    @staticmethod
    def _parse_gitignore(gitignore_content: str) -> list:
        """Parses the content of a .gitignore file and extracts the patterns.

This method reads the content of a .gitignore file, processes each line, and returns a list of patterns that are not comments or empty lines. It is used internally by the `_load_gitignore_patterns` method to process the .gitignore file content.

Args:
    gitignore_content (str): The content of the .gitignore file.

Returns:
    list: A list of patterns extracted from the .gitignore file.

Raises:
    None

Note:
    This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It helps in handling .gitignore files to ensure that untracked and modified content is managed effectively."""
        patterns = []
        for line in gitignore_content.splitlines():
            line = line.strip()
            if line and (not line.startswith('#')):
                patterns.append(line)
        return patterns

    @staticmethod
    def _split_gitignore_patterns(gitignore_patterns: list) -> tuple:
        """Splits gitignore patterns into folder and file patterns.

This method takes a list of gitignore patterns and separates them into two lists: one for folder patterns and one for file patterns. Folder patterns are identified by patterns that end with a slash.

Args:
    gitignore_patterns (list): A list of gitignore patterns to be split.

Returns:
    tuple: A tuple containing two lists, the first for folder patterns and the second for file patterns.

Raises:
    None

Note:
    This method is used internally by the GitignoreChecker class to process gitignore patterns. It is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate."""
        folder_patterns = ['.git', '.github', '.idea', 'venv', '.venv']
        file_patterns = []
        for pattern in gitignore_patterns:
            if pattern.endswith('/'):
                folder_patterns.append(pattern.rstrip('/'))
            else:
                file_patterns.append(pattern)
        return (folder_patterns, file_patterns)

    @staticmethod
    def _is_ignored(path: str, patterns: list, is_dir: bool=False) -> bool:
        """Checks if a given path is ignored based on a list of patterns.

This method iterates over a list of patterns and checks if the given path matches any of them using `fnmatch.fnmatch`. If the path is a directory, it also checks if the pattern ends with a slash and matches the path without the trailing slash.

Args:
    path (str): The path to check.
    patterns (list): A list of patterns to match against the path.
    is_dir (bool): Whether the path represents a directory. Defaults to False.

Returns:
    bool: True if the path is ignored, False otherwise.

Raises:
    None

Note:
    This method is used internally by the `check_files_and_folders` method to filter out ignored files and directories. It is a crucial part of the documentation generation and management tool, ensuring that untracked and ignored files are not included in the documentation process."""
        for pattern in patterns:
            if fnmatch.fnmatch(path, pattern):
                return True
            if is_dir and pattern.endswith('/') and fnmatch.fnmatch(path, pattern[:-1]):
                return True
        return False

    def check_files_and_folders(self) -> list:
        """Checks and returns a list of files and folders that are not ignored based on the project's ignore list and specific patterns.

This method walks through the directory tree, filtering out directories and files that match the ignore patterns or are listed in the project's ignore list. It specifically includes Python files that are not ignored.

Args:
    None

Returns:
    list: A list of relative paths to files and folders that are not ignored.

Raises:
    None

Note:
    This method uses the `SettingsManager` class to retrieve the project's ignore list and the `_is_ignored` method to check if a path should be ignored. The tool is part of a comprehensive system designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate."""
        ignored_folders = SettingsManager().get_setting().project.ignore_list
        not_ignored_files = []
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if not self._is_ignored(d, self.folder_patterns, is_dir=True) and (not any([d in i for i in ignored_folders]))]
            not_ignored_files += [os.path.relpath(os.path.join(root, d), self.directory) for d in dirs]
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.directory)
                if not self._is_ignored(file, self.file_patterns) and file_path.endswith('.py'):
                    not_ignored_files.append(relative_path)
        return not_ignored_files