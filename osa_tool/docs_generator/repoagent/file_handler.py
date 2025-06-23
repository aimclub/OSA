import ast
import json
import os
import astor
import git
from colorama import Fore, Style
from tqdm import tqdm

from osa_tool.docs_generator.repoagent.settings import SettingsManager
from osa_tool.docs_generator.repoagent.utils.gitignore_checker import GitignoreChecker
from osa_tool.docs_generator.repoagent.utils.meta_info_utils import latest_verison_substring
from osa_tool.utils import logger


class FileHandler:
    """FileHandler class for handling file operations in a repository.

A class to manage file operations such as reading, writing, and generating file structures in a repository. It also provides methods to retrieve code information and convert file structures to Markdown format.

Args:
    repo_path (str): The path to the repository.
    file_path (str): The path to the file within the repository.

Attributes:
    file_path (str): The path to the file within the repository.
    repo_path (str): The path to the repository.
    project_hierarchy (Path): The path to the project hierarchy file.

Methods:

read_file
Reads the content of a file.

Args:
    None

Returns:
    str: The content of the file.

Raises:
    FileNotFoundError: If the file does not exist.

get_obj_code_info
Retrieves detailed information about a code object (function, class, etc.).

Args:
    code_type (str): The type of the code object (e.g., 'FunctionDef', 'ClassDef').
    code_name (str): The name of the code object.
    start_line (int): The starting line number of the code object.
    end_line (int): The ending line number of the code object.
    params (list): The parameters of the code object.
    file_path (str, optional): The path to the file. Defaults to None.
    docstring (str, optional): The docstring of the code object. Defaults to ''.
    source_node (ast.AST, optional): The AST node of the code object. Defaults to None.

Returns:
    dict: A dictionary containing detailed information about the code object.

write_file
Writes content to a file.

Args:
    file_path (str): The path to the file within the repository.
    content (str): The content to write to the file.

Returns:
    None

Raises:
    IOError: If the file cannot be written.

get_modified_file_versions
Retrieves the current and previous versions of a file.

Args:
    None

Returns:
    tuple: A tuple containing the current and previous versions of the file.

Raises:
    git.exc.GitCommandError: If the Git command fails.

get_end_lineno
Retrieves the end line number of an AST node.

Args:
    node (ast.AST): The AST node.

Returns:
    int: The end line number of the node.

add_parent_references
Adds parent references to AST nodes.

Args:
    node (ast.AST): The AST node.
    parent (ast.AST, optional): The parent AST node. Defaults to None.

Returns:
    None

get_functions_and_classes
Retrieves functions and classes from a code content.

Args:
    code_content (str): The content of the code.

Returns:
    list: A list of tuples containing information about functions and classes.

generate_file_structure
Generates the structure of a file.

Args:
    file_path (str): The path to the file within the repository.

Returns:
    list: A list of dictionaries containing the file structure.

generate_overall_structure
Generates the overall structure of the repository.

Args:
    file_path_reflections (list): A list of file path reflections.
    jump_files (list): A list of files to skip.

Returns:
    dict: A dictionary containing the overall structure of the repository.

Raises:
    ValueError: If an error occurs while generating the file structure.

convert_to_markdown_file
Converts the file structure to a Markdown format.

Args:
    file_path (str, optional): The path to the file. Defaults to None.

Returns:
    str: The Markdown representation of the file structure.

Raises:
    ValueError: If no file object is found for the given file path."""

    def __init__(self, repo_path, file_path):
        """Initializes a FileHandler instance.

Sets the file path and repository path for the instance. Additionally, retrieves project hierarchy settings and assigns them to the instance.

Args:
    repo_path (str): The path to the repository.
    file_path (str): The path to the file within the repository.

Returns:
    None

Raises:
    None

Note:
    The project hierarchy is derived from the settings managed by the SettingsManager. This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository."""
        self.file_path = file_path
        self.repo_path = repo_path
        setting = SettingsManager.get_setting()
        self.project_hierarchy = setting.project.target_repo / setting.project.hierarchy_name

    def read_file(self):
        """Reads the content of a file.

Reads the content of a file specified by the file path and returns it as a string. This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository.

Args:
    self: The instance of the FileHandler class.
    file_path (str): The relative path of the file to be read.

Returns:
    str: The content of the file.

Raises:
    FileNotFoundError: If the file specified by the file path does not exist.
    IOError: If an error occurs while reading the file.

Note:
    This method constructs the absolute file path by joining the repository path and the file path. It then opens the file in read mode with UTF-8 encoding and reads its content. The tool integrates various functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories."""
        abs_file_path = os.path.join(self.repo_path, self.file_path)
        with open(abs_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        return content

    def get_obj_code_info(self, code_type, code_name, start_line, end_line, params, file_path=None, docstring='', source_node=None):
        """Retrieves detailed information about a code object (function or class) from a file.

This method constructs a dictionary containing various details about the specified code object, including its type, name, start and end line numbers, parameters, docstring, and whether it has a return statement. It reads the code content from the specified file and calculates the column position of the code object's name. This information is used by other methods such as `generate_file_structure` and `add_new_item` to gather detailed information about code objects in a file.

Args:
    code_type (str): The type of the code object (e.g., 'function', 'class').
    code_name (str): The name of the code object.
    start_line (int): The starting line number of the code object.
    end_line (int): The ending line number of the code object.
    params (list): A list of parameters for the code object.
    file_path (str, optional): The path to the file containing the code object. Defaults to None.
    docstring (str, optional): The docstring of the code object. Defaults to an empty string.
    source_node (object, optional): The source node of the code object. Defaults to None.

Returns:
    dict: A dictionary containing detailed information about the code object, including:
        - 'type' (str): The type of the code object.
        - 'name' (str): The name of the code object.
        - 'md_content' (list): A list to store Markdown content.
        - 'code_start_line' (int): The starting line number of the code object.
        - 'code_end_line' (int): The ending line number of the code object.
        - 'params' (list): A list of parameters for the code object.
        - 'docstring' (str): The docstring of the code object.
        - 'source_node' (object): The source node of the code object.
        - 'have_return' (bool): Whether the code object contains a return statement.
        - 'code_content' (str): The content of the code object.
        - 'name_column' (int): The column position of the code object's name.

Raises:
    FileNotFoundError: If the specified file does not exist.

Note:
    This method is a crucial part of the documentation generation process, ensuring that all necessary details about code objects are accurately captured and used to update the repository's documentation."""
        code_info = {}
        code_info['type'] = code_type
        code_info['name'] = code_name
        code_info['md_content'] = []
        code_info['code_start_line'] = start_line
        code_info['code_end_line'] = end_line
        code_info['params'] = params
        code_info['docstring'] = docstring
        code_info['source_node'] = source_node
        with open(os.path.join(self.repo_path, file_path if file_path != None else self.file_path), 'r', encoding='utf-8') as code_file:
            lines = code_file.readlines()
            code_content = ''.join(lines[start_line - 1:end_line])
            name_column = lines[start_line - 1].find(code_name)
            if 'return' in code_content:
                have_return = True
            else:
                have_return = False
            code_info['have_return'] = have_return
            code_info['code_content'] = code_content
            code_info['name_column'] = name_column
        return code_info

    def write_file(self, file_path, content):
        """Writes the content to a file at the specified file path within the repository.

This method ensures that the file path is correctly formatted and that the necessary directories are created if they do not exist. The content is written to the file using UTF-8 encoding.

Args:
    file_path (str): The relative path of the file within the repository. If the path starts with a slash, it will be removed.
    content (str): The content to be written to the file.

Returns:
    None

Raises:
    FileNotFoundError: If the repository path does not exist.
    IOError: If there is an error writing to the file.

Note:
    This method is used by other components, such as `Runner.add_new_item` and `Runner.process_file_changes`, to write generated Markdown content to files. It is a crucial part of the documentation automation process, ensuring that files are created and updated accurately within the repository."""
        if file_path.startswith('/'):
            file_path = file_path[1:]
        abs_file_path = os.path.join(self.repo_path, file_path)
        os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
        with open(abs_file_path, 'w', encoding='utf-8') as file:
            file.write(content)

    def get_modified_file_versions(self):
        """Retrieves the current and previous versions of a file in a Git repository.

This method reads the current version of the file from the file system and retrieves the previous version from the most recent commit that modified the file. If the file has not been modified in any commit, the previous version will be `None`.

Args:
    self (FileHandler): The instance of the `FileHandler` class.

Returns:
    tuple: A tuple containing two elements:
        - str: The current version of the file.
        - str or None: The previous version of the file, or `None` if no previous version exists.

Raises:
    FileNotFoundError: If the current file does not exist at the specified path.
    git.exc.GitError: If there is an error accessing the Git repository.

Note:
    This method is used in conjunction with other methods to track changes in file content over time, which is essential for automating the generation and management of documentation in a Git repository."""
        repo = git.Repo(self.repo_path)
        current_version_path = os.path.join(self.repo_path, self.file_path)
        with open(current_version_path, 'r', encoding='utf-8') as file:
            current_version = file.read()
        commits = list(repo.iter_commits(paths=self.file_path, max_count=1))
        previous_version = None
        if commits:
            commit = commits[0]
            try:
                previous_version = (commit.tree / self.file_path).data_stream.read().decode('utf-8')
            except KeyError:
                previous_version = None
        return (current_version, previous_version)

    def get_end_lineno(self, node):
        """Gets the end line number of a given AST node.

This method traverses the AST node and its children to determine the maximum end line number. If the node or any of its children do not have a line number, it returns -1.

Args:
    node (ast.AST): The AST node to get the end line number for.

Returns:
    int: The end line number of the node. Returns -1 if the node or any of its children do not have a line number.

Raises:
    None

Note:
    This method is used by the `get_functions_and_classes` method to determine the end line number of functions and classes in the parsed code. It is a crucial part of the file handling functionality, which is essential for the automated generation and management of documentation for a Git repository."""
        if not hasattr(node, 'lineno'):
            return -1
        end_lineno = node.lineno
        for child in ast.iter_child_nodes(node):
            child_end = getattr(child, 'end_lineno', None) or self.get_end_lineno(child)
            if child_end > -1:
                end_lineno = max(end_lineno, child_end)
        return end_lineno

    def add_parent_references(self, node, parent=None):
        """Adds parent references to all child nodes in the AST.

This method recursively traverses the Abstract Syntax Tree (AST) and assigns a reference to the parent node for each child node. This ensures that all nodes in the AST have a reference to their parent, which is useful for various analyses and transformations.

Args:
    node (ast.AST): The current node in the AST to which parent references will be added.
    parent (ast.AST, optional): The parent node of the current node. Defaults to None.

Returns:
    None: This method does not return any value.

Raises:
    None: This method does not raise any exceptions.

Note:
    This method is used internally by the `get_functions_and_classes` method to ensure that all nodes in the AST have a reference to their parent node. This is particularly useful for generating accurate and detailed documentation for the codebase, as it helps in understanding the structure and relationships between different parts of the code."""
        for child in ast.iter_child_nodes(node):
            child.parent = node
            self.add_parent_references(child, node)

    def get_functions_and_classes(self, code_content):
        """Retrieves functions and classes from the given code content.

This method parses the provided code content using the Abstract Syntax Tree (AST) and extracts information about functions and classes, including their names, line numbers, parameters, and docstrings. It is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository.

Args:
    code_content (str): The code content to parse.

Returns:
    list: A list of tuples, each containing the following information about a function or class:
        - type (str): The type of the node (e.g., "FunctionDef", "ClassDef", "AsyncFunctionDef").
        - name (str): The name of the function or class.
        - start_line (int): The starting line number of the function or class.
        - end_line (int): The ending line number of the function or class.
        - parameters (list): A list of parameter names for the function (empty for classes).
        - docstring (str): The docstring of the function or class.
        - node (ast.AST): The AST node object.

Raises:
    None

Note:
    This method uses the `get_end_lineno` method to determine the end line number of functions and classes. It also calls the `add_parent_references` method to ensure that all nodes in the AST have a reference to their parent node. This method is crucial for generating accurate and detailed documentation for the repository."""
        tree = ast.parse(code_content)
        self.add_parent_references(tree)
        functions_and_classes = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                start_line = node.lineno
                end_line = self.get_end_lineno(node)
                parameters = [arg.arg for arg in node.args.args] if 'args' in dir(node) else []
                all_names = [item[1] for item in functions_and_classes]
                functions_and_classes.append((type(node).__name__, node.name, start_line, end_line, parameters, ast.get_docstring(node), node))
        return functions_and_classes

    def generate_file_structure(self, file_path):
        """Generates the file structure for a given file path.

This method checks if the provided file path is a directory. If it is, it returns a list containing a single dictionary representing the directory. If it is a file, it reads the file content, extracts information about functions and classes using the `get_functions_and_classes` method, and constructs a list of dictionaries containing detailed information about each code object using the `get_obj_code_info` method.

Args:
    file_path (str): The path to the file or directory to generate the structure for.

Returns:
    list: A list of dictionaries, each containing detailed information about a code object or directory. The dictionary includes:
        - 'type' (str): The type of the code object (e.g., 'function', 'class') or 'Dir' for directories.
        - 'name' (str): The name of the code object or directory.
        - 'content' (str): The content of the code object (empty for directories).
        - 'md_content' (list): A list to store Markdown content (empty for directories).
        - 'code_start_line' (int): The starting line number of the code object (or -1 for directories).
        - 'code_end_line' (int): The ending line number of the code object (or -1 for directories).
        - 'params' (list): A list of parameters for the code object (empty for directories).
        - 'docstring' (str): The docstring of the code object (empty for directories).
        - 'source_node' (object): The source node of the code object (None for directories).

Raises:
    None

Note:
    This method is used by other methods such as `generate_overall_structure` to gather detailed information about code objects in a file. It relies on the `get_functions_and_classes` and `get_obj_code_info` methods to extract and format the necessary information. The generated file structure is essential for the automated documentation generation process, ensuring that all code elements are accurately represented."""
        if os.path.isdir(os.path.join(self.repo_path, file_path)):
            return [{'type': 'Dir', 'name': file_path, 'content': '', 'md_content': [], 'code_start_line': -1, 'code_end_line': -1}]
        else:
            with open(os.path.join(self.repo_path, file_path), 'r', encoding='utf-8') as f:
                content = f.read()
                structures = self.get_functions_and_classes(content)
                file_objects = []
                for struct in structures:
                    structure_type, name, start_line, end_line, params, docstring, source_node = struct
                    code_info = self.get_obj_code_info(structure_type, name, start_line, end_line, params, file_path, docstring, source_node)
                    file_objects.append(code_info)
        return file_objects

    def generate_overall_structure(self, file_path_reflections, jump_files) -> dict:
        """Generates the overall structure of the repository, excluding ignored files and specified jump files.

This method iterates over all files and folders in the repository that are not ignored according to the .gitignore file. It skips files that are in the `jump_files` list or end with a specific substring. For each valid file, it generates a detailed file structure using the `generate_file_structure` method and constructs a dictionary representing the repository structure.

Args:
    file_path_reflections (list): A list of file paths to reflect.
    jump_files (list): A list of file paths to skip.

Returns:
    dict: A dictionary where the keys are file paths and the values are lists of dictionaries, each containing detailed information about a code object or directory.

Raises:
    None

Note:
    This method relies on the `GitignoreChecker` class to filter out ignored files and the `generate_file_structure` method to gather detailed information about code objects in a file. The tool is part of a comprehensive system designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate."""
        repo_structure = {}
        gitignore_checker = GitignoreChecker(directory=self.repo_path, gitignore_path=os.path.join(self.repo_path, '.gitignore'))
        bar = tqdm(gitignore_checker.check_files_and_folders())
        for not_ignored_files in bar:
            normal_file_names = not_ignored_files
            if not_ignored_files in jump_files:
                print(f'{Fore.LIGHTYELLOW_EX}[File-Handler] Unstaged AddFile, ignore this file: {Style.RESET_ALL}{normal_file_names}')
                continue
            elif not_ignored_files.endswith(latest_verison_substring):
                print(f'{Fore.LIGHTYELLOW_EX}[File-Handler] Skip Latest Version, Using Git-Status Version]: {Style.RESET_ALL}{normal_file_names}')
                continue
            try:
                repo_structure[normal_file_names] = self.generate_file_structure(not_ignored_files)
            except Exception as e:
                logger.error(f'Alert: An error occurred while generating file structure for {not_ignored_files}: {e}')
                continue
            bar.set_description(f'generating repo structure: {not_ignored_files}')
        return repo_structure
