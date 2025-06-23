import itertools
import os
import git
from colorama import Fore, Style
from osa_tool.docs_generator.repoagent.settings import SettingsManager
from osa_tool.utils import logger

latest_verison_substring = '_latest_version.py'


def make_fake_files():
    """Creates fake files for untracked and modified files in the repository.

This method first deletes any existing fake files using the `delete_fake_files` method. It then retrieves the project settings and initializes a Git repository object. The method processes unstaged changes and untracked files, creating fake files for Python files and handling modified files by renaming them to a temporary name. It also prints messages to the console to indicate the actions taken.

Args:
    None

Returns:
    tuple: A tuple containing two elements:
        - file_path_reflections (dict): A dictionary mapping original file paths to their temporary file paths.
        - jump_files (list): A list of untracked Python files that were skipped.

Raises:
    None

Note:
    - The method uses the `SettingsManager` class to retrieve the project settings.
    - The method prints messages to the console to indicate the actions taken, such as skipping untracked files, saving the latest version of code, and creating temporary files for deleted but not staged files.
    - The `latest_version_substring` is a string that identifies temporary files.
    - The method uses color codes to format the console output for better readability.
    - This tool is part of a comprehensive system designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate."""
    delete_fake_files()
    setting = SettingsManager.get_setting()
    repo = git.Repo(setting.project.target_repo)
    unstaged_changes = repo.index.diff(None)
    untracked_files = repo.untracked_files
    jump_files = []
    for file_name in untracked_files:
        if file_name.endswith('.py'):
            print(f'{Fore.LIGHTMAGENTA_EX}[SKIP untracked files]: {Style.RESET_ALL}{file_name}')
            jump_files.append(file_name)
    for diff_file in unstaged_changes.iter_change_type('A'):
        if diff_file.a_path.endswith(latest_verison_substring):
            logger.error(
                'FAKE_FILE_IN_GIT_STATUS detected! suggest to use `delete_fake_files` and re-generate document')
            exit()
        jump_files.append(diff_file.a_path)
    file_path_reflections = {}
    for diff_file in itertools.chain(unstaged_changes.iter_change_type('M'), unstaged_changes.iter_change_type('D')):
        if diff_file.a_path.endswith(latest_verison_substring):
            logger.error(
                'FAKE_FILE_IN_GIT_STATUS detected! suggest to use `delete_fake_files` and re-generate document')
            exit()
        now_file_path = diff_file.a_path
        if now_file_path.endswith('.py'):
            raw_file_content = diff_file.a_blob.data_stream.read().decode('utf-8')
            latest_file_path = now_file_path[:-3] + latest_verison_substring
            if os.path.exists(os.path.join(setting.project.target_repo, now_file_path)):
                os.rename(os.path.join(setting.project.target_repo, now_file_path),
                          os.path.join(setting.project.target_repo, latest_file_path))
                print(
                    f'{Fore.LIGHTMAGENTA_EX}[Save Latest Version of Code]: {Style.RESET_ALL}{now_file_path} -> {latest_file_path}')
            else:
                print(
                    f'{Fore.LIGHTMAGENTA_EX}[Create Temp-File for Deleted(But not Staged) Files]: {Style.RESET_ALL}{now_file_path} -> {latest_file_path}')
                try:
                    with open(os.path.join(setting.project.target_repo, latest_file_path), 'w',
                              encoding='utf-8') as writer:
                        pass
                except:
                    pass
            try:
                with open(os.path.join(setting.project.target_repo, now_file_path), 'w', encoding='utf-8') as writer:
                    writer.write(raw_file_content)
            except:
                pass
            file_path_reflections[now_file_path] = latest_file_path
    return (file_path_reflections, jump_files)


def delete_fake_files():
    """Deletes fake files and recovers the latest version of modified files.

This method recursively traverses the target repository to find and delete temporary files that end with a specific substring. It also recovers the latest version of modified files by renaming them back to their original names.

Args:
    None

Returns:
    None

Raises:
    None

Note:
    - The method uses the `SettingsManager` class to retrieve the project settings.
    - The method prints messages to the console to indicate the actions taken, such as deleting temporary files or recovering the latest version of files.
    - The `latest_version_substring` is a string that identifies temporary files.
    - The method uses color codes to format the console output for better readability.
    - This function is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It helps in maintaining an up-to-date and accurate documentation by handling untracked and modified content efficiently."""
    setting = SettingsManager.get_setting()

    def gci(filepath):
        """Recursively deletes temporary files and recovers the latest version of files in a directory.

This method traverses the directory tree starting from the given filepath. It checks each file and directory, and if a file ends with a specific substring (`latest_version_substring`), it attempts to delete the corresponding original file and then either deletes the temporary file if it is empty or renames it to the original file name.

Args:
    filepath (str): The path to the directory to be processed.

Returns:
    None: This method does not return any value.

Raises:
    FileNotFoundError: If the specified filepath does not exist.
    PermissionError: If the method does not have permission to access or modify files.

Note:
    This method uses the `os` and `Fore` modules for file operations and colored console output. The `latest_version_substring` and `setting.project.target_repo` are assumed to be defined elsewhere in the code. The tool is part of a larger project aimed at automating the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate."""
        files = os.listdir(filepath)
        for fi in files:
            fi_d = os.path.join(filepath, fi)
            if os.path.isdir(fi_d):
                gci(fi_d)
            elif fi_d.endswith(latest_verison_substring):
                origin_name = fi_d.replace(latest_verison_substring, '.py')
                if os.path.exists(origin_name):
                    os.remove(origin_name)
                if os.path.getsize(fi_d) == 0:
                    print(
                        f'{Fore.LIGHTRED_EX}[Deleting Temp File]: {Style.RESET_ALL}{fi_d[len(str(setting.project.target_repo)):]}, {origin_name[len(str(setting.project.target_repo)):]}')
                    os.remove(fi_d)
                else:
                    print(
                        f'{Fore.LIGHTRED_EX}[Recovering Latest Version]: {Style.RESET_ALL}{origin_name[len(str(setting.project.target_repo)):]} <- {fi_d[len(str(setting.project.target_repo)):]}')
                    os.rename(fi_d, origin_name)

    gci(setting.project.target_repo)
