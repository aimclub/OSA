"""存储doc对应的信息，同时处理引用的关系"""
from __future__ import annotations
import ast
import json
import os
import threading
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, auto, unique
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import jedi
from colorama import Fore, Style
from prettytable import PrettyTable
from tqdm import tqdm

from osa_tool.docs_generator.repoagent.file_handler import FileHandler
from osa_tool.docs_generator.repoagent.multi_task_dispatch import TaskManager, Task
from osa_tool.docs_generator.repoagent.settings import SettingsManager
from osa_tool.docs_generator.repoagent.utils.docstring_updater import remove_docstrings
from osa_tool.docs_generator.repoagent.utils.meta_info_utils import latest_verison_substring
from osa_tool.utils import logger


@unique
class EdgeType(Enum):
    """Enum representing different types of edges.

This class defines an enumeration for different types of edges used in the system to categorize relationships between files and directories, such as reference edges, subfile edges, and file item edges. These edge types are crucial for the automated generation and management of documentation in a Git repository, helping to track and reflect the current state of the codebase.

Args:
    value (auto): Automatically assigned value for each enum member.

Returns:
    EdgeType: An instance of the EdgeType enum.

Raises:
    ValueError: If an invalid value is used to create an EdgeType instance.

Note:
    This enum is used to categorize edges in the system, which are essential for the tool's functionality in detecting changes, handling file operations, and generating accurate documentation."""
    reference_edge = auto()
    subfile_edge = auto()
    file_item_edge = auto()

@unique
class DocItemType(Enum):
    """DocItemType Enum

Represents different types of documentation items in a repository.

Attributes:
    _repo (DocItemType): Represents the repository.
    _dir (DocItemType): Represents a directory.
    _file (DocItemType): Represents a file.
    _class (DocItemType): Represents a class.
    _class_function (DocItemType): Represents a function within a class.
    _function (DocItemType): Represents a standalone function.
    _sub_function (DocItemType): Represents a sub-function.
    _global_var (DocItemType): Represents a global variable.

Methods:
    to_str (self) -> str:
        Converts the DocItemType to a string representation.

        Returns:
            str: The string representation of the DocItemType.

    print_self (self) -> str:
        Returns a colored string representation of the DocItemType.

        Returns:
            str: The colored string representation of the DocItemType.

    get_edge_type (self, from_item_type: DocItemType, to_item_type: DocItemType) -> Any:
        Determines the edge type between two DocItemType instances.

        Args:
            from_item_type (DocItemType): The source item type.
            to_item_type (DocItemType): The target item type.

        Returns:
            Any: The edge type between the two item types."""
    _repo = auto()
    _dir = auto()
    _file = auto()
    _class = auto()
    _class_function = auto()
    _function = auto()
    _sub_function = auto()
    _global_var = auto()

    def to_str(self):
        """Converts the `DocItemType` enum value to a string representation.

This method provides a human-readable string for different types of documentation items, which is particularly useful in the context of generating JSON representations of file hierarchies, as seen in the `to_hierarchy_json` method of the `MetaInfo` class.

Args:
    self (DocItemType): The enum instance to convert.

Returns:
    str: The string representation of the enum value. Possible values are 'ClassDef', 'FunctionDef', 'Dir', or the name of the enum value.

Raises:
    None

Note:
    This method is a crucial part of the documentation generation process, ensuring that different types of documentation items are accurately represented in string form. It is used extensively in the project to automate the creation and management of documentation for a Git repository."""
        if self == DocItemType._class:
            return 'ClassDef'
        elif self == DocItemType._function:
            return 'FunctionDef'
        elif self == DocItemType._class_function:
            return 'FunctionDef'
        elif self == DocItemType._sub_function:
            return 'FunctionDef'
        elif self == DocItemType._dir:
            return 'Dir'
        return self.name

    def print_self(self):
        """Prints the name of the `DocItemType` with a color-coded prefix.

This method returns a string representation of the `DocItemType` with a color prefix based on the type of the item. The color is determined by the specific `DocItemType` instance. This method is used internally by the `DocItem` class to format the output of the item type, ensuring that the documentation generated is visually distinct and easy to read.

Args:
    self (DocItemType): The `DocItemType` instance.

Returns:
    str: The color-coded string representation of the `DocItemType`.

Raises:
    None

Note:
    This method is part of the comprehensive tool designed to automate the generation and management of documentation for a Git repository. It helps in maintaining up-to-date and accurate documentation by providing clear and visually distinct item type representations."""
        color = Fore.WHITE
        if self == DocItemType._dir:
            color = Fore.GREEN
        elif self == DocItemType._file:
            color = Fore.YELLOW
        elif self == DocItemType._class:
            color = Fore.RED
        elif self in [DocItemType._function, DocItemType._sub_function, DocItemType._class_function]:
            color = Fore.BLUE
        return color + self.name + Style.RESET_ALL


@unique
class DocItemStatus(Enum):
    """DocItemStatus Enum

Represents the status of a documentation item.

Attributes:
    doc_up_to_date (DocItemStatus): The documentation is up to date.
    doc_has_not_been_generated (DocItemStatus): The documentation has not been generated.
    code_changed (DocItemStatus): The code has changed since the last documentation.
    add_new_referencer (DocItemStatus): A new referencer has been added.
    referencer_not_exist (DocItemStatus): A referencer no longer exists.

Note:
    This enum is used to track the status of documentation items in the `DocItem` class. It helps in automating the detection and management of changes in the codebase, ensuring that the documentation remains accurate and up-to-date."""
    doc_up_to_date = auto()
    doc_has_not_been_generated = auto()
    code_changed = auto()
    add_new_referencer = auto()
    referencer_not_exist = auto()

def need_to_generate(doc_item: DocItem, ignore_list: List[str]=[]) -> bool:
    """Determines whether a documentation item needs to be generated based on its status and file path.

This function checks if the documentation item is up to date. If not, it traverses the hierarchy to determine if the file path should be ignored based on the provided ignore list. It is a crucial part of the automated documentation generation tool, ensuring that only necessary documentation is processed and generated.

Args:
    doc_item (DocItem): The documentation item to check.
    ignore_list (List[str]): A list of file paths to ignore. Defaults to an empty list.

Returns:
    bool: True if the documentation item needs to be generated, False otherwise.

Raises:
    None

Note:
    This method is used in various parts of the codebase to determine if a documentation item should be processed. It is called by methods such as `check_has_task`, `print_recursive`, `generate_doc_for_a_single_item`, and `generate_doc`. The tool automates the detection of changes, generation of summaries, and handling of file operations to streamline the documentation process for software repositories."""
    if doc_item.item_status == DocItemStatus.doc_up_to_date:
        return False
    rel_file_path = doc_item.get_full_name()
    doc_item = doc_item.father
    while doc_item:
        if doc_item.item_type == DocItemType._file:
            if any((rel_file_path.startswith(ignore_item) for ignore_item in ignore_list)):
                return False
            else:
                return True
        doc_item = doc_item.father
    return False

@dataclass
class DocItem:
    """DocItem Class

Represents a documentation item in a repository, such as a file, directory, class, or function. This class is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It integrates various functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories.

Attributes:
    item_type (DocItemType): The type of the documentation item. Defaults to DocItemType._class_function.
    item_status (DocItemStatus): The status of the documentation item. Defaults to DocItemStatus.doc_has_not_been_generated.
    obj_name (str): The name of the object. Defaults to an empty string.
    code_start_line (int): The starting line number of the code. Defaults to -1.
    code_end_line (int): The ending line number of the code. Defaults to -1.
    source_node (Optional[ast.__ast.stmt]): The abstract syntax tree node of the source code. Defaults to None.
    md_content (List[str]): The markdown content of the documentation. Defaults to an empty list.
    content (Dict[Any, Any]): Additional content information. Defaults to an empty dictionary.
    children (Dict[str, DocItem]): Child documentation items. Defaults to an empty dictionary.
    father (Optional[DocItem]): The parent documentation item. Defaults to None.
    depth (int): The depth of the item in the hierarchy. Defaults to 0.
    tree_path (List[DocItem]): The path from the root to this item. Defaults to an empty list.
    max_reference_ansce (Optional[DocItem]): The maximum reference ancestor. Defaults to None.
    reference_who (List[DocItem]): Items that this item references. Defaults to an empty list.
    who_reference_me (List[DocItem]): Items that reference this item. Defaults to an empty list.
    special_reference_type (List[bool]): Special reference types. Defaults to an empty list.
    reference_who_name_list (List[str]): Names of items that this item references. Defaults to an empty list.
    who_reference_me_name_list (List[str]): Names of items that reference this item. Defaults to an empty list.
    has_task (bool): Indicates if the item has a task. Defaults to False.
    multithread_task_id (int): The task ID for multithreading. Defaults to -1."""
    item_type: DocItemType = DocItemType._class_function
    item_status: DocItemStatus = DocItemStatus.doc_has_not_been_generated
    obj_name: str = ''
    code_start_line: int = -1
    code_end_line: int = -1
    source_node: Optional[ast.__ast.stmt] = None
    md_content: List[str] = field(default_factory=list)
    content: Dict[Any, Any] = field(default_factory=dict)
    children: Dict[str, DocItem] = field(default_factory=dict)
    father: Any[DocItem] = None
    depth: int = 0
    tree_path: List[DocItem] = field(default_factory=list)
    max_reference_ansce: Any[DocItem] = None
    reference_who: List[DocItem] = field(default_factory=list)
    who_reference_me: List[DocItem] = field(default_factory=list)
    special_reference_type: List[bool] = field(default_factory=list)
    reference_who_name_list: List[str] = field(default_factory=list)
    who_reference_me_name_list: List[str] = field(default_factory=list)
    has_task: bool = False
    multithread_task_id: int = -1

    @staticmethod
    def has_ans_relation(now_a: DocItem, now_b: DocItem):
        """Checks if there is an ancestral relationship between two `DocItem` objects.

Determines if one `DocItem` is an ancestor of another in the hierarchical tree structure, which is useful for managing and organizing documentation items in the repository.

Args:
    now_a (DocItem): The first `DocItem` object to check.
    now_b (DocItem): The second `DocItem` object to check.

Returns:
    DocItem: The `DocItem` object that is an ancestor of the other, or `None` if no ancestral relationship exists.

Note:
    This method is part of the comprehensive tool designed to automate the generation and management of documentation for a Git repository. It helps in maintaining an accurate and up-to-date hierarchical structure of documentation items."""
        if now_b in now_a.tree_path:
            return now_b
        if now_a in now_b.tree_path:
            return now_a
        return None

    def get_travel_list(self):
        """Retrieves a list of all `DocItem` instances in the current hierarchy, including the current instance and all its descendants.

This method is particularly useful for tasks that require processing all items in a tree structure, such as generating comprehensive documentation for a Git repository.

Args:
    None

Returns:
    List[DocItem]: A list of `DocItem` instances representing the current item and all its children.

Raises:
    None

Note:
    This method is used to traverse the hierarchy of `DocItem` instances, which is essential for automating the generation and management of documentation in the repository. It ensures that all relevant items are included in the documentation process, maintaining accuracy and completeness."""
        now_list = [self]
        for _, child in self.children.items():
            now_list = now_list + child.get_travel_list()
        return now_list

    def check_depth(self):
        """Checks the depth of the current `DocItem` and its children.

This method recursively calculates the depth of the current `DocItem` based on the maximum depth of its children. The depth of a `DocItem` is defined as the number of levels of children it contains. This method is particularly useful for ensuring that the hierarchical structure of documentation items is accurately reflected, which is essential for generating clear and organized documentation.

Args:
    None

Returns:
    int: The depth of the current `DocItem`.

Raises:
    None

Note:
    This method is typically called after the hierarchical structure of `DocItem` objects has been built to ensure that the depth information is accurate. It is an integral part of the documentation generation process, helping to maintain a well-structured and organized document hierarchy."""
        if len(self.children) == 0:
            self.depth = 0
            return self.depth
        max_child_depth = 0
        for _, child in self.children.items():
            child_depth = child.check_depth()
            max_child_depth = max(child_depth, max_child_depth)
        self.depth = max_child_depth + 1
        return self.depth

    def parse_tree_path(self, now_path):
        """Parses the tree path for the current DocItem and its children.

This method recursively processes the current DocItem and its children to build a tree structure that represents the documentation hierarchy. It is an essential part of the documentation generation process, ensuring that the tree structure is accurately updated to reflect the current state of the repository.

Args:
    now_path (List[DocItem]): The current path in the tree structure. This list contains the sequence of DocItem objects from the root to the current item.

Returns:
    None: This method modifies the tree structure in place and does not return any value.

Raises:
    None: This method does not raise any exceptions.

Note:
    This method is called recursively to build the tree structure for all children of the current DocItem. It is a key component in the automated documentation generation and management tool, which aims to streamline the documentation process for Git repositories."""
        self.tree_path = now_path + [self]
        for key, child in self.children.items():
            child.parse_tree_path(self.tree_path)

    def get_file_name(self):
        """Generates the file name of the current `DocItem`.

This method constructs the file name of the `DocItem` by splitting the full name obtained from `get_full_name` and ensuring the file extension is `.py`. It is a crucial part of the documentation generation process, helping to create accurate and consistent file paths for various documentation tasks.

Args:
    None

Returns:
    str: The file name of the `DocItem` with a `.py` extension.

Raises:
    None

Note:
    This method is used in various parts of the codebase, such as generating file paths for markdown documents and parsing references between code items. It ensures that the file names are correctly formatted and consistent with the project's structure."""
        full_name = self.get_full_name()
        return full_name.split('.py')[0] + '.py'

    def get_full_name(self, strict=False):
        """Generates the full name of the current `DocItem` in a hierarchical format.

This method constructs the full name of the `DocItem` by traversing up the hierarchy and concatenating the names of each parent `DocItem`. If the `strict` parameter is set to `True`, it ensures that the name used is the exact name from the parent's children dictionary, appending a suffix if there are duplicates.

Args:
    strict (bool): If `True`, ensures the name used is the exact name from the parent's children dictionary and appends a suffix if there are duplicates. Defaults to `False`.

Returns:
    str: The full hierarchical name of the `DocItem`.

Raises:
    None

Note:
    This method is used in various parts of the codebase, such as generating prompts for chat engines and parsing references between code items. It is a crucial component in maintaining accurate and up-to-date documentation for the Git repository."""
        if self.father == None:
            return self.obj_name
        name_list = []
        now = self
        while now != None:
            self_name = now.obj_name
            if strict:
                for name, item in self.father.children.items():
                    if item == now:
                        self_name = name
                        break
                if self_name != now.obj_name:
                    self_name = self_name + '(name_duplicate_version)'
            name_list = [self_name] + name_list
            now = now.father
        name_list = name_list[1:]
        return '/'.join(name_list)

    def find(self, recursive_file_path: list) -> Optional[DocItem]:
        """Finds a `DocItem` in the hierarchical tree based on the provided file path.

This method traverses the hierarchical tree of documentation items to find the `DocItem` that corresponds to the given file path. If any part of the path does not exist in the tree, the method returns `None`.

Args:
    recursive_file_path (list): A list of strings representing the file path to be traversed.

Returns:
    Optional[DocItem]: The `DocItem` corresponding to the provided file path, or `None` if the path does not exist in the tree.

Raises:
    AssertionError: If the `item_type` of the current `DocItem` is not `DocItemType._repo`.

Note:
    This method is used in conjunction with the `DocItemType` enum to ensure that the traversal starts from a repository-level item. It is a crucial part of the automated documentation generation and management tool, which aims to streamline the documentation process for Git repositories by automating the detection of changes, generation of summaries, and handling of file operations."""
        assert self.item_type == DocItemType._repo
        pos = 0
        now = self
        while pos < len(recursive_file_path):
            if not recursive_file_path[pos] in now.children.keys():
                return None
            now = now.children[recursive_file_path[pos]]
            pos += 1
        return now

    @staticmethod
    def check_has_task(now_item: DocItem, ignore_list: List[str]=[]):
        """Checks if a documentation item or any of its children need to be generated.

This method traverses the hierarchy of documentation items to determine if any item needs to be generated based on the `need_to_generate` function. If any item or its children need to be generated, the `has_task` attribute of the current item is set to `True`.

Args:
    now_item (DocItem): The current documentation item to check.
    ignore_list (List[str]): A list of file paths to ignore. Defaults to an empty list.

Returns:
    None

Raises:
    None

Note:
    This method is used to determine if any documentation tasks need to be performed on the current item or its children. It is called by methods such as `diff` in the `main.py` module. The tool automates the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and reflects the current state of the codebase."""
        if need_to_generate(now_item, ignore_list=ignore_list):
            now_item.has_task = True
        for _, child in now_item.children.items():
            DocItem.check_has_task(child, ignore_list)
            now_item.has_task = child.has_task or now_item.has_task

    def print_recursive(self, indent=0, print_content=False, diff_status=False, ignore_list: List[str]=[]):
        """Prints the hierarchical structure of documentation items recursively.

This method prints the hierarchical structure of documentation items, optionally including their status and content. It uses indentation to represent the hierarchy level and color-codes the item types for better readability. This functionality is particularly useful for visualizing the project structure and debugging.

Args:
    indent (int): The current indentation level. Defaults to 0.
    print_content (bool): Whether to print the content of the items. Defaults to False.
    diff_status (bool): Whether to include the status of the items. Defaults to False.
    ignore_list (List[str]): A list of file paths to ignore. Defaults to an empty list.

Returns:
    None

Raises:
    None

Note:
    This method is used to display the hierarchical structure of documentation items, which can be useful for debugging and visualizing the project structure. It is called by methods such as `run` and `diff` in the `main.py` module."""

        def print_indent(indent=0):
            if indent == 0:
                return ''
            return '  ' * indent + '|-'
        print_obj_name = self.obj_name
        setting = SettingsManager.get_setting()
        if self.item_type == DocItemType._repo:
            print_obj_name = setting.project.target_repo
        if diff_status and need_to_generate(self, ignore_list=ignore_list):
            print(print_indent(indent) + f'{self.item_type.print_self()}: {print_obj_name} : {self.item_status.name}')
        else:
            print(print_indent(indent) + f'{self.item_type.print_self()}: {print_obj_name}')
        for child_name, child in self.children.items():
            if diff_status and child.has_task == False:
                continue
            child.print_recursive(indent=indent + 1, print_content=print_content, diff_status=diff_status, ignore_list=ignore_list)

def find_all_referencer(repo_path, variable_name, file_path, line_number, column_number, in_file_only=False):
    """Finds all references to a variable in a repository or within a file.

This method uses the `jedi` library to find references to a specified variable in a given file or across the entire repository. It filters the references to match the variable name and excludes the reference at the specified line and column.

Args:
    repo_path (str): The root path of the repository.
    variable_name (str): The name of the variable to find references for.
    file_path (str): The path of the file relative to the repository root.
    line_number (int): The line number where the variable is defined.
    column_number (int): The column number where the variable is defined.
    in_file_only (bool): If True, only find references within the specified file. Defaults to False.

Returns:
    list: A list of tuples containing the relative file path, line number, and column number of each reference. If an error occurs, an empty list is returned.

Raises:
    Exception: If an error occurs during the reference search, it is logged and an empty list is returned.

Note:
    See also: `walk_file` method in the `MetaInfo` class for an example of how this function is used to parse references."""
    script = jedi.Script(path=os.path.join(repo_path, file_path))
    try:
        if in_file_only:
            references = script.get_references(line=line_number, column=column_number, scope='file')
        else:
            references = script.get_references(line=line_number, column=column_number)
        variable_references = [ref for ref in references if ref.name == variable_name]
        return [(os.path.relpath(ref.module_path, repo_path), ref.line, ref.column) for ref in variable_references if not (ref.line == line_number and ref.column == column_number)]
    except Exception as e:
        logger.error(f'Error occurred: {e}')
        logger.error(f'Parameters: variable_name={variable_name}, file_path={file_path}, line_number={line_number}, column_number={column_number}')
        return []

@dataclass
class MetaInfo:
    """MetaInfo Class

Represents metadata information for a repository, including its structure, version, and various attributes for managing documentation and references.

Attributes:
    repo_path (Path): The path to the repository. Defaults to an empty string.
    document_version (str): The version of the document. Defaults to an empty string.
    main_idea (str): The main idea or purpose of the repository. Defaults to an empty string.
    repo_structure (Dict[str, Any]): The structure of the repository. Defaults to an empty dictionary.
    target_repo_hierarchical_tree (DocItem): The hierarchical tree representation of the repository. Defaults to an empty DocItem.
    white_list (List): A list of whitelisted items. Defaults to None.
    fake_file_reflection (Dict[str, str]): A dictionary mapping fake file names to their actual names. Defaults to an empty dictionary.
    jump_files (List[str]): A list of files to be ignored. Defaults to an empty list.
    deleted_items_from_older_meta (List[List]): A list of items deleted from the older metadata. Defaults to an empty list.
    in_generation_process (bool): Indicates if the document generation process is in progress. Defaults to False.
    checkpoint_lock (threading.Lock): A lock for checkpoint operations. Defaults to a new threading.Lock.

Methods:
    init_meta_info(file_path_reflections, jump_files) -> MetaInfo:
        Initializes the MetaInfo object from the given file path reflections and jump files.

        Args:
            file_path_reflections (Dict[str, str]): A dictionary mapping file paths to their reflections.
            jump_files (List[str]): A list of files to be ignored.

        Returns:
            MetaInfo: The initialized MetaInfo object.

    from_checkpoint_path(checkpoint_dir_path: Path, repo_structure: Optional[Dict[str, Any]]=None) -> MetaInfo:
        Loads the MetaInfo object from a checkpoint directory.

        Args:
            checkpoint_dir_path (Path): The path to the checkpoint directory.
            repo_structure (Optional[Dict[str, Any]]): The structure of the repository. Defaults to None.

        Returns:
            MetaInfo: The loaded MetaInfo object.

    checkpoint(target_dir_path: str | Path, flash_reference_relation=False):
        Saves the current state of the MetaInfo object to a checkpoint directory.

        Args:
            target_dir_path (str | Path): The path to the target directory.
            flash_reference_relation (bool): Whether to flash the reference relation. Defaults to False.

    print_task_list(task_dict: Dict[Task]):
        Prints a table of tasks.

        Args:
            task_dict (Dict[Task]): A dictionary of tasks.

    get_all_files(count_repo=False) -> List[DocItem]:
        Retrieves all files in the repository.

        Args:
            count_repo (bool): Whether to include repository items. Defaults to False.

        Returns:
            List[DocItem]: A list of all files.

    find_obj_with_lineno(file_node: DocItem, start_line_num) -> DocItem:
        Finds an object in the file node based on the line number.

        Args:
            file_node (DocItem): The file node to search in.
            start_line_num (int): The starting line number.

        Returns:
            DocItem: The found object.

    parse_reference():
        Parses references within the repository.

    get_task_manager(now_node: DocItem, task_available_func) -> TaskManager:
        Generates a task manager for the given node and task availability function.

        Args:
            now_node (DocItem): The current node.
            task_available_func (Callable): A function to determine if a task is available.

        Returns:
            TaskManager: The generated task manager.

    get_topology(task_available_func) -> TaskManager:
        Generates the topology of tasks.

        Args:
            task_available_func (Callable): A function to determine if a task is available.

        Returns:
            TaskManager: The generated topology.

    _map(deal_func: Callable):
        Applies a function to all items in the repository.

        Args:
            deal_func (Callable): The function to apply.

    load_doc_from_older_meta(older_meta: MetaInfo):
        Loads documentation from an older version of MetaInfo.

        Args:
            older_meta (MetaInfo): The older MetaInfo object.

    from_project_hierarchy_path(repo_path: str) -> MetaInfo:
        Loads the MetaInfo object from a project hierarchy path.

        Args:
            repo_path (str): The path to the repository.

        Returns:
            MetaInfo: The loaded MetaInfo object.

    to_hierarchy_json(flash_reference_relation=False) -> Dict:
        Converts the repository structure to a JSON format.

        Args:
            flash_reference_relation (bool): Whether to flash the reference relation. Defaults to False.

        Returns:
            Dict: The JSON representation of the repository structure.

    from_project_hierarchy_json(project_hierarchy_json, repo_structure: Optional[Dict[str, Any]]=None) -> MetaInfo:
        Loads the MetaInfo object from a project hierarchy JSON.

        Args:
            project_hierarchy_json (Dict): The JSON representation of the project hierarchy.
            repo_structure (Optional[Dict[str, Any]]): The structure of the repository. Defaults to None.

        Returns:
            MetaInfo: The loaded MetaInfo object."""
    repo_path: Path = ''
    document_version: str = ''
    main_idea: str = ''
    repo_structure: Dict[str, Any] = field(default_factory=dict)
    target_repo_hierarchical_tree: 'DocItem' = field(default_factory=lambda: DocItem())
    white_list: Any[List] = None
    fake_file_reflection: Dict[str, str] = field(default_factory=dict)
    jump_files: List[str] = field(default_factory=list)
    deleted_items_from_older_meta: List[List] = field(default_factory=list)
    in_generation_process: bool = False
    checkpoint_lock: threading.Lock = threading.Lock()

    @staticmethod
    def init_meta_info(file_path_reflections, jump_files) -> MetaInfo:
        """Initializes the MetaInfo object for the repository.

This method initializes a `MetaInfo` object by generating the overall structure of the repository using the `FileHandler` class. It retrieves the project settings, prints an initialization message, and constructs the repository structure from the provided file path reflections and jump files. The `MetaInfo` object is then populated with the repository path, file path reflections, and jump files.

Args:
    file_path_reflections (list): A list of file path reflections.
    jump_files (list): A list of files to skip.

Returns:
    MetaInfo: A `MetaInfo` object representing the repository's hierarchical structure.

Raises:
    ValueError: If an error occurs while generating the file structure.

Note:
    This method uses the `SettingsManager` to retrieve project settings and the `FileHandler` class to generate the repository structure. It also logs information about deleted and blank files. The project is designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate."""
        setting = SettingsManager.get_setting()
        project_abs_path = setting.project.target_repo
        print(f'{Fore.LIGHTRED_EX}Initializing MetaInfo: {Style.RESET_ALL}from {project_abs_path}')
        file_handler = FileHandler(project_abs_path, None)
        repo_structure = file_handler.generate_overall_structure(file_path_reflections, jump_files)
        metainfo = MetaInfo.from_project_hierarchy_json(repo_structure)
        metainfo.repo_path = project_abs_path
        metainfo.fake_file_reflection = file_path_reflections
        metainfo.jump_files = jump_files
        return metainfo

    @staticmethod
    def from_checkpoint_path(checkpoint_dir_path: Path, repo_structure: Optional[Dict[str, Any]]=None) -> MetaInfo:
        """Loads and constructs a `MetaInfo` object from a checkpoint directory.

This method reads the project hierarchy and meta-info JSON files from the specified checkpoint directory. It then constructs a `MetaInfo` object representing the repository structure, including files, directories, and their relationships. The method also sets additional attributes on the `MetaInfo` object using project settings. This is particularly useful for automating the generation and management of documentation for a Git repository, ensuring that the documentation reflects the current state of the codebase.

Args:
    checkpoint_dir_path (Path): The path to the checkpoint directory containing the JSON files.
    repo_structure (Optional[Dict[str, Any]]): An optional dictionary representing the repository structure. Defaults to None.

Returns:
    MetaInfo: A `MetaInfo` object representing the repository's hierarchical structure.

Raises:
    None

Note:
    This method uses the `SettingsManager` to retrieve project settings and logs the loading process. It is part of a comprehensive tool designed to automate the documentation process for software repositories."""
        setting = SettingsManager.get_setting()
        project_hierarchy_json_path = checkpoint_dir_path / 'project_hierarchy.json'
        with open(project_hierarchy_json_path, 'r', encoding='utf-8') as reader:
            project_hierarchy_json = json.load(reader)
        metainfo = MetaInfo.from_project_hierarchy_json(project_hierarchy_json, repo_structure)
        with open(checkpoint_dir_path / 'meta-info.json', 'r', encoding='utf-8') as reader:
            meta_data = json.load(reader)
            metainfo.repo_path = setting.project.target_repo
            metainfo.main_idea = meta_data['main_idea']
            metainfo.document_version = meta_data['doc_version']
            metainfo.fake_file_reflection = meta_data['fake_file_reflection']
            metainfo.jump_files = meta_data['jump_files']
            metainfo.in_generation_process = meta_data['in_generation_process']
            metainfo.deleted_items_from_older_meta = meta_data['deleted_items_from_older_meta']
        print(f'{Fore.CYAN}Loading MetaInfo:{Style.RESET_ALL} {checkpoint_dir_path}')
        return metainfo

    def checkpoint(self, target_dir_path: str | Path, flash_reference_relation=False):
        """Saves the current state of the `MetaInfo` object to a specified directory.

This method ensures that the current state of the `MetaInfo` object is saved to a specified directory. It creates the directory if it does not exist and saves two JSON files: `project_hierarchy.json` and `meta-info.json`. The `project_hierarchy.json` file contains the hierarchical structure of the repository, while the `meta-info.json` file contains metadata about the project. This is particularly useful for checkpointing the repository state and ensuring that the metadata is up-to-date, which is essential for the automated generation and management of documentation for a Git repository.

Args:
    target_dir_path (str | Path): The path to the directory where the checkpoint files will be saved.
    flash_reference_relation (bool): If `True`, includes detailed reference information for each item in the hierarchy. Defaults to `False`.

Returns:
    None

Raises:
    IOError: If there is an error saving the JSON files to the specified directory.

Note:
    This method is a crucial part of the project's functionality to automate the documentation process, ensuring that changes are detected and documented accurately. It helps in maintaining up-to-date and accurate documentation, which is essential for large repositories where manual tracking and updating can be time-consuming and error-prone."""
        with self.checkpoint_lock:
            target_dir = Path(target_dir_path)
            logger.debug(f'Checkpointing MetaInfo to directory: {target_dir}')
            print(f'{Fore.GREEN}MetaInfo is Refreshed and Saved{Style.RESET_ALL}')
            if not target_dir.exists():
                target_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f'Created directory: {target_dir}')
            now_hierarchy_json = self.to_hierarchy_json(flash_reference_relation=flash_reference_relation)
            hierarchy_file = target_dir / 'project_hierarchy.json'
            try:
                with hierarchy_file.open('w', encoding='utf-8') as writer:
                    json.dump(now_hierarchy_json, writer, indent=2, ensure_ascii=False)
                logger.debug(f'Saved hierarchy JSON to {hierarchy_file}')
            except IOError as e:
                logger.error(f'Failed to save hierarchy JSON to {hierarchy_file}: {e}')
            meta_info_file = target_dir / 'meta-info.json'
            meta = {'main_idea': SettingsManager().get_setting().project.main_idea,
                    'doc_version': self.document_version,
                    'in_generation_process': self.in_generation_process,
                    'fake_file_reflection': self.fake_file_reflection,
                    'jump_files': self.jump_files,
                    'deleted_items_from_older_meta': self.deleted_items_from_older_meta}
            try:
                with meta_info_file.open('w', encoding='utf-8') as writer:
                    json.dump(meta, writer, indent=2, ensure_ascii=False)
                logger.debug(f'Saved meta-info JSON to {meta_info_file}')
            except IOError as e:
                logger.error(f'Failed to save meta-info JSON to {meta_info_file}: {e}')

    def print_task_list(self, task_dict: Dict[Task]):
        """Prints a table of tasks with their details.

Prints a table containing the task ID, document generation reason, path, and dependencies for each task in the provided task dictionary. This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository, integrating various functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories.

Args:
    task_dict (Dict[Task]): A dictionary mapping task IDs to Task objects.

Returns:
    None

Raises:
    None

Note:
    This method is used to display the current task list, which is useful for debugging and monitoring the progress of document generation. It helps ensure that the documentation process is transparent and manageable, especially in large repositories where manual tracking can be challenging."""
        task_table = PrettyTable(['task_id', 'Doc Generation Reason', 'Path', 'dependency'])
        for task_id, task_info in task_dict.items():
            remain_str = 'None'
            if task_info.dependencies != []:
                remain_str = ','.join([str(d_task.task_id) for d_task in task_info.dependencies])
                if len(remain_str) > 20:
                    remain_str = remain_str[:8] + '...' + remain_str[-8:]
            task_table.add_row([task_id, task_info.extra_info.item_status.name, task_info.extra_info.get_full_name(strict=True), remain_str])
        print(task_table)

    def get_all_files(self, count_repo=False) -> List[DocItem]:
        """Retrieves all files, directories, and optionally repositories from the hierarchical tree.

This method is part of a comprehensive tool designed to automate the generation and management of documentation for a Git repository. It integrates various functionalities to detect changes, handle file operations, manage project settings, and generate summaries for modules and directories.

Args:
    count_repo (bool): If True, includes repositories in the result. Defaults to False.

Returns:
    List[DocItem]: A list of all files, directories, and optionally repositories.

Note:
    This method traverses the hierarchical tree starting from the target repository and collects all items of type file, directory, and optionally repository. It is particularly useful for ensuring that the documentation reflects the current state of the codebase, especially in large repositories where manual tracking can be challenging."""
        files = []

        def walk_tree(now_node):
            if now_node.item_type in [DocItemType._file, DocItemType._dir]:
                files.append(now_node)
            if count_repo and now_node.item_type == DocItemType._repo:
                files.append(now_node)
            for _, child in now_node.children.items():
                walk_tree(child)
        walk_tree(self.target_repo_hierarchical_tree)
        return files

    def find_obj_with_lineno(self, file_node: DocItem, start_line_num) -> DocItem:
        """Finds the documentation item corresponding to a given line number.

This method traverses the hierarchy of documentation items to find the most specific item that contains the specified line number. It is particularly useful for parsing and referencing code elements within a larger documentation structure, which is a key part of the project's automated documentation generation and management for Git repositories.

Args:
    file_node (DocItem): The root node of the documentation hierarchy.
    start_line_num (int): The line number to find.

Returns:
    DocItem: The documentation item that contains the specified line number.

Raises:
    AssertionError: If the file_node or any child content is None.

Note:
    This method is used to locate the specific documentation item that corresponds to a given line number in a file, aiding in the accurate and efficient management of documentation for the repository."""
        now_node = file_node
        assert now_node != None
        while len(now_node.children) > 0:
            find_qualify_child = False
            for _, child in now_node.children.items():
                assert child.content != None
                if child.content['code_start_line'] <= start_line_num and child.content['code_end_line'] >= start_line_num:
                    now_node = child
                    find_qualify_child = True
                    break
            if not find_qualify_child:
                return now_node
        return now_node

    def parse_reference(self):
        """Parses bidirectional references for all files in the repository.

This method iterates through all files in the repository, excluding jump files and files not in the white list. It detects references to objects within the same file and handles special cases such as references from unstaged or untracked files. It updates the reference relationships between objects and counts the number of references found.

Args:
    None

Returns:
    None

Raises:
    AssertionError: If a file name ends with the latest version substring or if a file path is found in the jump files list.

Note:
    - This method is used in the `get_topology` and `load_doc_from_older_meta` methods to ensure that the reference relationships are up-to-date.
    - It uses the `get_all_files` method to retrieve all files in the repository.
    - It uses the `get_file_name` and `get_full_name` methods of the `DocItem` class to get file and full names of objects.
    - It uses the `find_all_referencer` function to find all references to a given object.
    - It uses the `find_obj_with_lineno` method to find an object based on its line number.
    - It uses the `has_ans_relation` method to check if two objects have a reference relationship."""
        file_nodes = self.get_all_files()
        white_list_file_names, white_list_obj_names = ([], [])
        if self.white_list != None:
            white_list_file_names = [cont['file_path'] for cont in self.white_list]
            white_list_obj_names = [cont['id_text'] for cont in self.white_list]
        for file_node in tqdm(file_nodes, desc='parsing bidirectional reference'):
            '检测一个文件内的所有引用信息，只能检测引用该文件内某个obj的其他内容。\n            1. 如果某个文件是jump-files，就不应该出现在这个循环里\n            2. 如果检测到的引用信息来源于一个jump-files, 忽略它\n            3. 如果检测到一个引用来源于fake-file,则认为他的母文件是原来的文件\n            '
            assert not file_node.get_full_name().endswith(latest_verison_substring)
            ref_count = 0
            rel_file_path = file_node.get_full_name()
            assert rel_file_path not in self.jump_files
            if white_list_file_names != [] and file_node.get_file_name() not in white_list_file_names:
                continue

            def walk_file(now_obj: DocItem):
                """在文件内遍历所有变量"""
                nonlocal ref_count, white_list_file_names
                in_file_only = False
                if white_list_obj_names != [] and now_obj.obj_name not in white_list_obj_names:
                    in_file_only = True
                if SettingsManager().get_setting().project.parse_references:
                    reference_list = find_all_referencer(repo_path=self.repo_path, variable_name=now_obj.obj_name, file_path=rel_file_path, line_number=now_obj.content['code_start_line'], column_number=now_obj.content['name_column'], in_file_only=in_file_only)
                else:
                    reference_list = []
                for referencer_pos in reference_list:
                    referencer_file_ral_path = referencer_pos[0]
                    if referencer_file_ral_path in self.fake_file_reflection.values():
                        '检测到的引用者来自于unstaged files，跳过该引用'
                        print(f'{Fore.LIGHTBLUE_EX}[Reference From Unstaged Version, skip]{Style.RESET_ALL} {referencer_file_ral_path} -> {now_obj.get_full_name()}')
                        continue
                    elif referencer_file_ral_path in self.jump_files:
                        '检测到的引用者来自于untracked files，跳过该引用'
                        print(f'{Fore.LIGHTBLUE_EX}[Reference From Unstracked Version, skip]{Style.RESET_ALL} {referencer_file_ral_path} -> {now_obj.get_full_name()}')
                        continue
                    target_file_hiera = referencer_file_ral_path.split('/')
                    referencer_file_item = self.target_repo_hierarchical_tree.find(target_file_hiera)
                    if referencer_file_item == None:
                        print(f'{Fore.LIGHTRED_EX}Error: Find "{referencer_file_ral_path}"(not in target repo){Style.RESET_ALL} referenced {now_obj.get_full_name()}')
                        continue
                    referencer_node = self.find_obj_with_lineno(referencer_file_item, referencer_pos[1])
                    if referencer_node.obj_name == now_obj.obj_name:
                        logger.info(f'Jedi find {now_obj.get_full_name()} with name_duplicate_reference, skipped')
                        continue
                    if DocItem.has_ans_relation(now_obj, referencer_node) == None:
                        if now_obj not in referencer_node.reference_who:
                            special_reference_type = referencer_node.item_type in [DocItemType._function, DocItemType._sub_function, DocItemType._class_function] and referencer_node.code_start_line == referencer_pos[1]
                            referencer_node.special_reference_type.append(special_reference_type)
                            referencer_node.reference_who.append(now_obj)
                            now_obj.who_reference_me.append(referencer_node)
                            ref_count += 1
                for _, child in now_obj.children.items():
                    walk_file(child)
            for _, child in file_node.children.items():
                walk_file(child)

    def get_task_manager(self, now_node: DocItem, task_available_func) -> TaskManager:
        """Retrieves a `TaskManager` instance for managing tasks based on the current `DocItem` hierarchy.

This method filters and sorts the `DocItem` instances based on a white list and a task availability function. It then creates tasks for each `DocItem` while handling dependencies and potential circular references. The tool is designed to automate the generation and management of documentation for a Git repository, ensuring that tasks are added in a topologically sorted order to maintain the integrity of the documentation process.

Args:
    now_node (DocItem): The current `DocItem` from which to generate the task list.
    task_available_func (Callable[[DocItem], bool]): A function that determines if a `DocItem` should be included in the task list.

Returns:
    TaskManager: A `TaskManager` instance containing the tasks for the `DocItem` hierarchy.

Raises:
    None

Note:
    - The method ensures that tasks are added in a topologically sorted order, handling dependencies and potential circular references.
    - If a circular reference is detected, a warning message is printed indicating the level and the item involved.
    - This method is part of a comprehensive tool that automates the detection of changes, generation of summaries, and handling of file operations for a Git repository."""
        doc_items = now_node.get_travel_list()
        if self.white_list != None:

            def in_white_list(item: DocItem):
                for cont in self.white_list:
                    if item.get_file_name() == cont['file_path'] and item.obj_name == cont['id_text']:
                        return True
                return False
            doc_items = list(filter(in_white_list, doc_items))
        doc_items = list(filter(task_available_func, doc_items))
        doc_items = sorted(doc_items, key=lambda x: x.depth)
        deal_items = []
        task_manager = TaskManager()
        bar = tqdm(total=len(doc_items), desc='parsing topology task-list')
        while doc_items:
            min_break_level = 10000000.0
            target_item = None
            for item in doc_items:
                '一个任务依赖于所有引用者和他的子节点,我们不能保证引用不成环(也许有些仓库的废代码会出现成环)。\n                这时就只能选择一个相对来说遵守程度最好的了\n                有特殊情况func-def中的param def可能会出现循环引用\n                另外循环引用真实存在，对于一些bind类的接口真的会发生，比如：\n                ChatDev/WareHouse/Gomoku_HumanAgentInteraction_20230920135038/main.py里面的: on-click、show-winner、restart\n                '
                best_break_level = 0
                second_best_break_level = 0
                for _, child in item.children.items():
                    if task_available_func(child) and child not in deal_items:
                        best_break_level += 1
                for referenced, special in zip(item.reference_who, item.special_reference_type):
                    if task_available_func(referenced) and referenced not in deal_items:
                        best_break_level += 1
                    if task_available_func(referenced) and (not special) and (referenced not in deal_items):
                        second_best_break_level += 1
                if best_break_level == 0:
                    min_break_level = -1
                    target_item = item
                    break
                if second_best_break_level < min_break_level:
                    target_item = item
                    min_break_level = second_best_break_level
            if min_break_level > 0:
                print(f'circle-reference(second-best still failed), level={min_break_level}: {target_item.get_full_name()}')
            item_denp_task_ids = []
            for _, child in target_item.children.items():
                if child.multithread_task_id != -1:
                    item_denp_task_ids.append(child.multithread_task_id)
            for referenced_item in target_item.reference_who:
                if referenced_item.multithread_task_id in task_manager.task_dict.keys():
                    item_denp_task_ids.append(referenced_item.multithread_task_id)
            item_denp_task_ids = list(set(item_denp_task_ids))
            if task_available_func == None or task_available_func(target_item):
                task_id = task_manager.add_task(dependency_task_id=item_denp_task_ids, extra=target_item)
                target_item.multithread_task_id = task_id
            deal_items.append(target_item)
            doc_items.remove(target_item)
            bar.update(1)
        return task_manager

    def get_topology(self, task_available_func) -> TaskManager:
        """Retrieves a `TaskManager` instance for managing tasks based on the current `DocItem` hierarchy.

This method ensures that tasks are added in a topologically sorted order, handling dependencies and potential circular references. It first calls `parse_reference` to update the reference relationships between objects, ensuring that the hierarchy is accurate and up-to-date. Then, it uses `get_task_manager` to create a `TaskManager` instance, which is responsible for managing tasks with dependencies.

Args:
    task_available_func (Callable[[DocItem], bool]): A function that determines if a `DocItem` should be included in the task list.

Returns:
    TaskManager: A `TaskManager` instance containing the tasks for the `DocItem` hierarchy.

Raises:
    None

Note:
    - This method ensures that tasks are added in a topologically sorted order, handling dependencies and potential circular references.
    - It uses the `parse_reference` method to update the reference relationships between objects.
    - It uses the `get_task_manager` method to generate the task list.
    - The `TaskManager` instance is crucial for automating the generation and management of documentation, ensuring that all tasks are processed efficiently and in the correct order."""
        self.parse_reference()
        task_manager = self.get_task_manager(self.target_repo_hierarchical_tree, task_available_func=task_available_func)
        return task_manager

    def load_doc_from_older_meta(self, older_meta: MetaInfo):
        """Merges documentation from an older version of metainfo into the current metainfo.

This method iterates through the hierarchical tree of the older metainfo and merges the documentation into the current metainfo. It updates the content and status of each item, identifies deleted items, and updates reference relationships.

Args:
    older_meta (MetaInfo): The older version of metainfo to merge from.

Returns:
    None

Raises:
    AssertionError: If a child item cannot be found in the current metainfo's hierarchical tree.

Note:
    - This method is used in the `diff` function to update the current metainfo with changes from an older version.
    - It uses the `find_item` helper method to locate items in the current metainfo's hierarchical tree.
    - It updates the `deleted_items_from_older_meta` list with items that were present in the older metainfo but are missing in the current metainfo.
    - It calls the `parse_reference` method to ensure that the reference relationships are up-to-date after merging."""
        logger.info('merge docs from an older version of metainfo')
        root_item = self.target_repo_hierarchical_tree
        deleted_items = []

        def find_item(now_item: DocItem) -> Optional[DocItem]:
            nonlocal root_item
            if now_item.father == None:
                return root_item
            father_find_result = find_item(now_item.father)
            if not father_find_result:
                return None
            real_name = None
            for child_real_name, temp_item in now_item.father.children.items():
                if temp_item == now_item:
                    real_name = child_real_name
                    break
            assert real_name != None
            if real_name in father_find_result.children.keys():
                result_item = father_find_result.children[real_name]
                return result_item
            return None

        def travel(now_older_item: DocItem):
            result_item = find_item(now_older_item)
            if not result_item:
                deleted_items.append([now_older_item.get_full_name(), now_older_item.item_type.name])
                return
            result_item.md_content = now_older_item.md_content
            result_item.item_status = now_older_item.item_status
            if 'code_content' in now_older_item.content.keys():
                assert 'code_content' in result_item.content.keys()
                if remove_docstrings(now_older_item.content['code_content']) != remove_docstrings(result_item.content['code_content']):
                    result_item.item_status = DocItemStatus.code_changed
            for _, child in now_older_item.children.items():
                travel(child)
        travel(older_meta.target_repo_hierarchical_tree)
        '接下来，parse现在的双向引用，观察谁的引用者改了'
        self.parse_reference()

        def travel2(now_older_item: DocItem):
            result_item = find_item(now_older_item)
            if not result_item:
                return
            'result_item引用的人是否变化了'
            new_reference_names = [name.get_full_name(strict=True) for name in result_item.who_reference_me]
            old_reference_names = now_older_item.who_reference_me_name_list
            if not set(new_reference_names) == set(old_reference_names) and result_item.item_status == DocItemStatus.doc_up_to_date:
                if set(new_reference_names) <= set(old_reference_names):
                    result_item.item_status = DocItemStatus.referencer_not_exist
                else:
                    result_item.item_status = DocItemStatus.add_new_referencer
            for _, child in now_older_item.children.items():
                travel2(child)
        travel2(older_meta.target_repo_hierarchical_tree)
        self.deleted_items_from_older_meta = deleted_items

    def to_hierarchy_json(self, flash_reference_relation=False):
        """Converts the file hierarchy to a JSON representation.

This method generates a JSON object that represents the hierarchical structure of files and directories in the repository. It includes detailed information about each item, such as its name, type, Markdown content, and status. If `flash_reference_relation` is set to `True`, it also includes detailed reference information.

Args:
    flash_reference_relation (bool): If `True`, includes detailed reference information for each item. Defaults to `False`.

Returns:
    dict: A JSON-like dictionary representing the hierarchical structure of files and directories.

Raises:
    None

Note:
    This method is used to serialize the file hierarchy for storage or transmission. It is particularly useful in the context of checkpointing the repository state, as seen in the `checkpoint` method of the `MetaInfo` class. The serialized JSON can be used to ensure that documentation is up-to-date and reflects the current state of the codebase, which is crucial for large repositories where manual tracking and updating of documentation can be time-consuming and error-prone."""
        hierachy_json = {}
        file_item_list = self.get_all_files()
        for file_item in file_item_list:
            file_hierarchy_content = []

            def walk_file(now_obj: DocItem):
                nonlocal file_hierarchy_content, flash_reference_relation
                temp_json_obj = now_obj.content
                if 'source_node' in temp_json_obj:
                    temp_json_obj.pop('source_node')
                temp_json_obj['name'] = now_obj.obj_name
                temp_json_obj['type'] = now_obj.item_type.to_str()
                temp_json_obj['md_content'] = now_obj.md_content
                temp_json_obj['item_status'] = now_obj.item_status.name
                if flash_reference_relation:
                    temp_json_obj['who_reference_me'] = [cont.get_full_name(strict=True) for cont in now_obj.who_reference_me]
                    temp_json_obj['reference_who'] = [cont.get_full_name(strict=True) for cont in now_obj.reference_who]
                    temp_json_obj['special_reference_type'] = now_obj.special_reference_type
                else:
                    temp_json_obj['who_reference_me'] = now_obj.who_reference_me_name_list
                    temp_json_obj['reference_who'] = now_obj.reference_who_name_list
                file_hierarchy_content.append(temp_json_obj)
                for _, child in now_obj.children.items():
                    walk_file(child)
            for _, child in file_item.children.items():
                walk_file(child)
            if file_item.item_type == DocItemType._dir:
                temp_json_obj = {}
                temp_json_obj['name'] = file_item.obj_name
                temp_json_obj['type'] = file_item.item_type.to_str()
                temp_json_obj['md_content'] = file_item.md_content
                temp_json_obj['item_status'] = file_item.item_status.name
                hierachy_json[file_item.get_full_name()] = [temp_json_obj]
            else:
                hierachy_json[file_item.get_full_name()] = file_hierarchy_content
        return hierachy_json

    @staticmethod
    def from_project_hierarchy_json(project_hierarchy_json, repo_structure: Optional[Dict[str, Any]]=None) -> MetaInfo:
        """Parses a project hierarchy JSON and constructs a `MetaInfo` object representing the repository structure.

This method takes a JSON representation of the project hierarchy and an optional repository structure dictionary. It constructs a `MetaInfo` object that represents the repository's hierarchical structure, including files, directories, and their relationships. The method also handles cases where files have been deleted or are empty. This tool is part of a comprehensive system designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and reflects the current state of the codebase.

Args:
    project_hierarchy_json (Dict[str, Any]): A dictionary representing the project hierarchy.
    repo_structure (Optional[Dict[str, Any]]): An optional dictionary representing the repository structure. Defaults to None.

Returns:
    MetaInfo: A `MetaInfo` object representing the repository's hierarchical structure.

Raises:
    AssertionError: If the `file_content` is not a list.

Note:
    This method uses the `SettingsManager` to retrieve project settings and the `DocItem` class to represent individual items in the hierarchy. It also logs information about deleted and blank files."""
        setting = SettingsManager.get_setting()
        target_meta_info = MetaInfo(repo_structure=project_hierarchy_json, target_repo_hierarchical_tree=DocItem(item_type=DocItemType._repo, obj_name='full_repo'))
        for file_name, file_content in tqdm(project_hierarchy_json.items(), desc='parsing parent relationship'):
            if not os.path.exists(os.path.join(setting.project.target_repo, file_name)):
                logger.info(f'deleted content: {file_name}')
                continue
            elif os.path.getsize(os.path.join(setting.project.target_repo, file_name)) == 0 and file_content and (file_content[0]['type'] != 'Dir'):
                logger.info(f'blank content: {file_name}')
                continue
            recursive_file_path = file_name.split('/')
            pos = 0
            now_structure = target_meta_info.target_repo_hierarchical_tree
            while pos < len(recursive_file_path) - 1:
                if recursive_file_path[pos] not in now_structure.children.keys():
                    now_structure.children[recursive_file_path[pos]] = DocItem(item_type=DocItemType._dir, md_content='', obj_name=recursive_file_path[pos])
                    now_structure.children[recursive_file_path[pos]].father = now_structure
                now_structure = now_structure.children[recursive_file_path[pos]]
                pos += 1
            if recursive_file_path[-1] not in now_structure.children.keys():
                if file_content and file_content[0].get('type') == 'Dir':
                    doctype = DocItemType._dir
                    now_structure.children[recursive_file_path[pos]] = DocItem(item_type=doctype, obj_name=recursive_file_path[-1])
                    now_structure.children[recursive_file_path[pos]].father = now_structure
                else:
                    doctype = DocItemType._file
                    now_structure.children[recursive_file_path[pos]] = DocItem(item_type=doctype, obj_name=recursive_file_path[-1])
                    now_structure.children[recursive_file_path[pos]].father = now_structure
            if repo_structure:
                actual_item = repo_structure[file_name]
            else:
                actual_item = deepcopy(file_content)
            assert type(file_content) == list
            file_item = target_meta_info.target_repo_hierarchical_tree.find(recursive_file_path)
            '用类线段树的方式：\n            1.先parse所有节点，再找父子关系\n            2.一个节点的父节点，所有包含他的code范围的节点里的，最小的节点\n            复杂度是O(n^2)\n            3.最后来处理节点的type问题\n            '
            obj_item_list: List[DocItem] = []
            for value, actual in zip(file_content, actual_item):
                if value.get('source_node'):
                    source_node = value.get('source_node')
                else:
                    source_node = actual.get('source_node')
                obj_doc_item = DocItem(obj_name=value['name'], content=value, md_content=value['md_content'], code_start_line=value.get('code_start_line'), code_end_line=value.get('code_end_line'), source_node=source_node)
                if 'item_status' in value.keys():
                    obj_doc_item.item_status = DocItemStatus[value['item_status']]
                if 'reference_who' in value.keys():
                    obj_doc_item.reference_who_name_list = value['reference_who']
                if 'special_reference_type' in value.keys():
                    obj_doc_item.special_reference_type = value['special_reference_type']
                if 'who_reference_me' in value.keys():
                    obj_doc_item.who_reference_me_name_list = value['who_reference_me']
                obj_item_list.append(obj_doc_item)
            for item in obj_item_list:
                potential_father = None
                for other_item in obj_item_list:

                    def code_contain(item, other_item) -> bool:
                        if other_item.code_end_line == item.code_end_line and other_item.code_start_line == item.code_start_line:
                            return False
                        if other_item.code_end_line < item.code_end_line or other_item.code_start_line > item.code_start_line:
                            return False
                        return True
                    if code_contain(item, other_item):
                        if potential_father == None or other_item.code_end_line - other_item.code_start_line < potential_father.code_end_line - potential_father.code_start_line:
                            potential_father = other_item
                if potential_father == None:
                    potential_father = file_item
                item.father = potential_father
                child_name = item.obj_name
                if child_name in potential_father.children.keys():
                    now_name_id = 0
                    while child_name + f'_{now_name_id}' in potential_father.children.keys():
                        now_name_id += 1
                    child_name = child_name + f'_{now_name_id}'
                    logger.warning(f'Name duplicate in {file_item.get_full_name()}: rename to {item.obj_name}->{child_name}')
                if potential_father.item_type != DocItemType._dir:
                    potential_father.children[child_name] = item

            def change_items(now_item: DocItem):
                if now_item.item_type == DocItemType._dir:
                    return target_meta_info
                if now_item.item_type != DocItemType._file:
                    if now_item.content['type'] == 'ClassDef':
                        now_item.item_type = DocItemType._class
                    elif now_item.content['type'] == 'FunctionDef':
                        now_item.item_type = DocItemType._function
                        if now_item.father.item_type == DocItemType._class:
                            now_item.item_type = DocItemType._class_function
                        elif now_item.father.item_type in [DocItemType._function, DocItemType._sub_function]:
                            now_item.item_type = DocItemType._sub_function
                for _, child in now_item.children.items():
                    change_items(child)
            change_items(file_item)
        target_meta_info.target_repo_hierarchical_tree.parse_tree_path(now_path=[])
        target_meta_info.target_repo_hierarchical_tree.check_depth()
        return target_meta_info