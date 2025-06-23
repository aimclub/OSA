import os
import re
import subprocess
import git
from colorama import Fore, Style

from osa_tool.docs_generator.repoagent.settings import SettingsManager


class ChangeDetector:
    """ChangeDetector is a class for detecting changes in Python files within a Git repository.

Attributes:
    repo_path (str): The path to the Git repository.
    repo (git.Repo): The Git repository object.

Methods:
    __init__(self, repo_path)
        Initializes the ChangeDetector with the specified repository path.

        Args:
            repo_path (str): The path to the Git repository.

    get_staged_pys(self)
        Retrieves staged Python files and their status (new or modified).

        Returns:
            dict: A dictionary mapping file paths to a boolean indicating if the file is new.

    get_file_diff(self, file_path, is_new_file)
        Retrieves the diff for a specific file.

        Args:
            file_path (str): The path to the file.
            is_new_file (bool): Whether the file is new.

        Returns:
            list: A list of diff lines.

    parse_diffs(self, diffs)
        Parses the diff lines to identify added and removed lines.

        Args:
            diffs (list): A list of diff lines.

        Returns:
            dict: A dictionary with 'added' and 'removed' keys, each mapping to a list of tuples (line_number, line_content).

    identify_changes_in_structure(self, changed_lines, structures)
        Identifies changes in specified structures within the diff.

        Args:
            changed_lines (dict): A dictionary with 'added' and 'removed' keys, each mapping to a list of tuples (line_number, line_content).
            structures (list): A list of tuples representing structures (structure_type, name, start_line, end_line, parent_structure).

        Returns:
            dict: A dictionary with 'added' and 'removed' keys, each mapping to a set of tuples (name, parent_structure).

    get_to_be_staged_files(self)
        Identifies files that should be staged based on certain conditions.

        Returns:
            list: A list of file paths that should be staged.

    add_unstaged_files(self)
        Adds unstaged files that meet certain conditions to the staging area.

        Returns:
            list: A list of file paths that were added to the staging area."""

    def __init__(self, repo_path):
        """Initializes the ChangeDetector instance.

Sets up the repository path and initializes a Git repository object. This method is crucial for the tool's ability to detect changes, manage file operations, and generate accurate documentation for the Git repository.

Args:
    repo_path (str): The path to the Git repository.

Raises:
    git.exc.InvalidGitRepositoryError: If the provided path is not a valid Git repository.

Note:
    This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It ensures that the repository is correctly set up for subsequent operations such as change detection and file management."""
        self.repo_path = repo_path
        self.repo = git.Repo(repo_path)


    def get_to_be_staged_files(self):
        """Retrieves a list of files that need to be staged based on the current repository state and project settings.

This method identifies untracked and unstaged files that meet certain conditions and adds them to a list of files to be staged. It prints intermediate results for debugging purposes.

Args:
    None

Returns:
    list[str]: A list of file paths that need to be staged.

Raises:
    None

Note:
    - The method uses the `SettingsManager` class to retrieve project settings.
    - The method prints the repository path, already staged files, untracked files, and newly staged files for debugging.
    - This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate."""
        to_be_staged_files = []
        staged_files = [item.a_path for item in self.repo.index.diff('HEAD')]
        print(f'{Fore.LIGHTYELLOW_EX}target_repo_path{Style.RESET_ALL}: {self.repo_path}')
        print(f'{Fore.LIGHTMAGENTA_EX}already_staged_files{Style.RESET_ALL}:{staged_files}')
        setting = SettingsManager.get_setting()
        project_hierarchy = setting.project.hierarchy_name
        diffs = self.repo.index.diff(None)
        untracked_files = self.repo.untracked_files
        print(f'{Fore.LIGHTCYAN_EX}untracked_files{Style.RESET_ALL}: {untracked_files}')
        for untracked_file in untracked_files:
            if untracked_file.startswith(setting.project.markdown_docs_name):
                to_be_staged_files.append(untracked_file)
            continue
            print(f'rel_untracked_file:{rel_untracked_file}')
            if rel_untracked_file.endswith('.md'):
                rel_untracked_file = os.path.relpath(rel_untracked_file, setting.project.markdown_docs_name)
                corresponding_py_file = os.path.splitext(rel_untracked_file)[0] + '.py'
                print(f'corresponding_py_file in untracked_files:{corresponding_py_file}')
                if corresponding_py_file in staged_files:
                    to_be_staged_files.append(
                        os.path.join(self.repo_path.lstrip('/'), setting.project.markdown_docs_name,
                                     rel_untracked_file))
            elif rel_untracked_file == project_hierarchy:
                to_be_staged_files.append(rel_untracked_file)
        unstaged_files = [diff.b_path for diff in diffs]
        print(f'{Fore.LIGHTCYAN_EX}unstaged_files{Style.RESET_ALL}: {unstaged_files}')
        for unstaged_file in unstaged_files:
            if unstaged_file.startswith(setting.project.markdown_docs_name) or unstaged_file.startswith(
                    setting.project.hierarchy_name):
                to_be_staged_files.append(unstaged_file)
            elif unstaged_file == project_hierarchy:
                to_be_staged_files.append(unstaged_file)
            continue
            abs_unstaged_file = os.path.join(self.repo_path, unstaged_file)
            rel_unstaged_file = os.path.relpath(abs_unstaged_file, self.repo_path)
            print(f'rel_unstaged_file:{rel_unstaged_file}')
            if unstaged_file.endswith('.md'):
                rel_unstaged_file = os.path.relpath(rel_unstaged_file, setting.project.markdown_docs_name)
                corresponding_py_file = os.path.splitext(rel_unstaged_file)[0] + '.py'
                print(f'corresponding_py_file:{corresponding_py_file}')
                if corresponding_py_file in staged_files:
                    to_be_staged_files.append(
                        os.path.join(self.repo_path.lstrip('/'), setting.project.markdown_docs_name, rel_unstaged_file))
            elif unstaged_file == project_hierarchy:
                to_be_staged_files.append(unstaged_file)
        print(f'{Fore.LIGHTRED_EX}newly_staged_files{Style.RESET_ALL}: {to_be_staged_files}')
        return to_be_staged_files

    def add_unstaged_files(self):
        """Adds unstaged files to the Git staging area.

This method retrieves a list of files that need to be staged based on the current repository state and project settings. It then adds these files to the Git staging area using the `git add` command.

Args:
    None

Returns:
    list[str]: A list of file paths that were added to the staging area.

Raises:
    None

Note:
    - The method uses the `get_to_be_staged_files` method to determine which files need to be staged.
    - The method prints intermediate results for debugging purposes.
    - This functionality is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and reflects the current state of the codebase."""
        unstaged_files_meeting_conditions = self.get_to_be_staged_files()
        for file_path in unstaged_files_meeting_conditions:
            add_command = f'git -C {self.repo.working_dir} add {file_path}'
            subprocess.run(add_command, shell=True, check=True)
        return unstaged_files_meeting_conditions
