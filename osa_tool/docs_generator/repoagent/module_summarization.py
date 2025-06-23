import os
from pathlib import Path
from typing import List, Dict, Any

from osa_tool.docs_generator.repoagent.settings import SettingsManager


def summarize_repository(root_dir: str, repo_structure, chat_engine) -> Dict[str, Any]:
    """Summarizes the repository by generating summaries for each directory and its subdirectories.

This function recursively traverses the directory structure of a given repository, identifies Python files, and generates summaries based on the provided repository structure and chat engine. It also handles ignored folders as specified in the settings. The tool is part of a comprehensive system designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate.

Args:
    root_dir (str): The root directory of the repository.
    repo_structure (Dict[str, Any]): A dictionary containing the structure of the repository, mapping file paths to their respective components.
    chat_engine (Any): The chat engine used to generate summaries.

Returns:
    Dict[str, Any]: A dictionary containing the summary of the repository, including the name, path, file summaries, submodules, and module summary for each directory.

Raises:
    ValueError: If the root directory does not exist or is not a valid directory.

Note:
    See also: The `summarize_modules` method in the `Runner` class for an example of how this function is used in a workflow."""

    def summarize_directory(directory: Path, repo_structure, chat_engine, root_dir) -> Dict[str, Any]:
        """Summarizes a directory by extracting summaries of Python files and subdirectories.

This method iterates over the items in the specified directory, collects Python files, and recursively processes subdirectories that are not in the ignored folders list. It then generates summaries for the Python files and combines them with summaries of subdirectories to create a module summary. The tool is part of a comprehensive system designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate.

Args:
    directory (Path): The directory to be summarized.
    repo_structure (Dict[str, Any]): A dictionary containing the structure of the repository, mapping file paths to their components.
    chat_engine (Any): The chat engine used to generate module summaries.
    root_dir (Path): The root directory of the repository.

Returns:
    Dict[str, Any]: A dictionary containing the name, path, file summaries, submodule summaries, and the module summary of the directory.

Raises:
    ValueError: If the directory does not exist or is not a valid directory.

Note:
    The method uses settings from the SettingsManager to determine ignored folders. This tool integrates various functionalities to detect changes, handle file operations, manage project settings, and generate summaries, making it particularly useful for large repositories where manual documentation can be time-consuming and error-prone."""
        settings = SettingsManager().get_setting()
        ignored_folders = settings.project.ignore_list
        file_paths = []
        subdir_paths = []
        for item in directory.iterdir():
            if item.is_file() and item.suffix == '.py':
                file_paths.append(item)
            elif item.is_dir() and str(item) not in ignored_folders:
                subdir_paths.append(item)
        file_summaries = []
        for file_path in file_paths:
            if file_path.is_file() and file_path.suffix == '.py':
                stripped_file_path = os.path.relpath(file_path, start=root_path)
                desc = [f'File {file_path} has such components:']
                if stripped_file_path in repo_structure and repo_structure[stripped_file_path]:
                    for obj in list(filter(lambda x: x['type'] in ['ClassDef', 'FunctionDef'],
                                           repo_structure[stripped_file_path])):
                        if obj['md_content']:
                            desc.append(f"{obj['type'][:-3]} {obj['name']}\n{obj['md_content'][-1].split('\n\n')[0]}")
                    if len(desc) > 1:
                        file_summaries.append('\n\n'.join(desc))
        submodule_summaries = list(filter(lambda x: x['module_summary'],
                                          [summarize_directory(subdir, repo_structure, chat_engine, root_dir) for subdir
                                           in subdir_paths]))
        submodules_summaries_text = [submod['module_summary'] for submod in submodule_summaries]
        if not file_summaries and (not submodules_summaries_text):
            module_summary = ''
        else:
            module_summary = create_module_summary(directory.name, file_summaries, submodules_summaries_text,
                                                   chat_engine)
        return {'name': directory.name, 'path': str(directory), 'file_summaries': file_summaries,
                'submodules': submodule_summaries, 'module_summary': module_summary}

    root_path = Path(root_dir)
    return summarize_directory(root_path, repo_structure, chat_engine, root_dir)


def create_module_summary(name: str, file_summaries: List[str], submodule_summaries: List[str], chat_engine) -> str:
    """Creates a summary for a module based on file and submodule summaries.

This method constructs a module summary by combining the name of the module, summaries of its files, and summaries of its submodules. It then uses a `ChatEngine` instance to generate a final summarized content. The tool is part of a comprehensive system designed to automate the generation and management of documentation for a Git repository, ensuring that documentation is up-to-date and accurate.

Args:
    name (str): The name of the module.
    file_summaries (List[str]): A list of summaries for the files within the module.
    submodule_summaries (List[str]): A list of summaries for the submodules within the module.
    chat_engine (ChatEngine): An instance of the `ChatEngine` class used to generate the final summary.

Returns:
    str: The summarized content of the module.

Raises:
    Exception: If an error occurs during the chat call with the language model.

Note:
    The `ChatEngine` class is used to manage and initialize project and chat completion settings. The `module_summary_template` is used to format the module description into messages. This method is crucial for maintaining accurate and up-to-date documentation in large repositories."""
    summary_content = [f'Module: {name}', '\n## Files Summary:\n\n- ' + '\n- '.join(file_summaries).replace('#', '##'),
                       '\n\n## Submodules Summary:\n\n- ' + '\n- '.join(submodule_summaries).replace('#', '##')]
    result = chat_engine.summarize_module('\n-----\n'.join(summary_content))
    return result
