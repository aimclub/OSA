import os
import re

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class RepositoryStructureTranslator:
    """
    RepositoryStructureTranslator translates directory and file names in a repository from a source language to English and updates code references accordingly.
    
        Class Methods:
        - __init__: Initializes the translator with configuration and sets up necessary attributes.
        - rename_directories_and_files: Orchestrates the complete translation process for both directories and files.
        - rename_directories: Translates directory names and updates code to reflect these changes.
        - rename_files: Translates file names while preserving their extensions.
        - translate_directories: Generates a mapping of original directory names to their translated English versions.
        - translate_files: Generates mappings for renaming files and updating code references.
        - _translate_text: Translates a given text string into English using an LLM, formatting the output.
        - _get_all_files: Recursively collects all file paths in the repository, excluding specified directories.
        - _get_all_directories: Recursively collects all directory paths in the repository, excluding specified directories.
        - update_code: Updates import statements and file paths within a single file based on a rename mapping.
        - _cycle_update_code: Iteratively updates all Python files in the repository using a rename mapping.
    
        Class Attributes:
        - config_manager: Central configuration manager instance.
        - model_settings: Settings for the translation model.
        - repo_url: URL of the target Git repository.
        - model_handler: Handler for model operations.
        - base_path: Local filesystem path where the repository is cloned.
        - excluded_dirs: Set of directory names to exclude from processing.
        - extensions_code_files: Set of file extensions considered as source code.
        - excluded_names: Set of base filenames to exclude from translation.
        - events: Log of events recorded during the translation process.
    
        The class automates the localization of repository structures by translating names and ensuring code integrity through systematic updates to file contents.
    """

    def __init__(self, config_manager: ConfigManager) -> None:
        """
        Initializes the RepositoryStructureTranslator instance.
        
        This constructor sets up the translator by loading configuration settings,
        initializing the model handler for general analysis, and defining file processing rules.
        The rules determine which directories and files are excluded from analysis and which file extensions are considered source code.
        
        Args:
            config_manager: Configuration manager providing access to model and repository settings.
        
        Class Fields:
            config_manager (ConfigManager): Central configuration manager instance.
            model_settings (ModelSettings): Settings for the general analysis model, retrieved from the configuration.
            repo_url (str): URL of the target Git repository, obtained from the Git settings.
            model_handler (ModelHandler): Handler for model operations, built from the general model settings.
            base_path (str): Local filesystem path where the repository is expected to be cloned. It is derived by joining the current working directory with a folder name parsed from the repository URL.
            excluded_dirs (set[str]): Directory names to exclude from analysis (e.g., '.git', '.venv'). This prevents processing version control and virtual environment directories.
            extensions_code_files (set[str]): File extensions considered as source code (e.g., '.py'). Only files with these extensions will be analyzed as code.
            excluded_names (set[str]): Base filenames (without extension) and specific filenames to exclude from analysis (e.g., 'main', 'license', 'readme', 'requirements', 'examples', 'docs', '.gitignore'). This avoids analyzing common non-source files and entry points that may not require structural translation.
            events (list[OperationEvent]): Log of events recorded during analysis, initially empty.
        """
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("general")
        self.repo_url = self.config_manager.get_git_settings().repository
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

        self.excluded_dirs = {".git", ".venv"}
        self.extensions_code_files = {".py"}
        self.excluded_names = {
            ".gitignore" "main",
            "license",
            "readme",
            "requirements",
            "examples",
            "docs",
        }

        self.events: list[OperationEvent] = []

    def rename_directories_and_files(self) -> dict:
        """
        The complete process of translating directories and files in the repository.
        
        This method orchestrates the renaming of both directories and files to English, updating any internal code references to maintain consistency. It logs the operation outcome as an event and returns a summary of changes.
        
        Why:
        Standardizing repository structure and file names into English improves accessibility and maintainability for international contributors. The method ensures the repository remains functional by updating references and provides a clear audit trail of the operation through events.
        
        Returns:
            A dictionary containing:
                - "result": A dictionary with keys "directories_renamed" and "files_renamed" indicating the count of renamed items.
                - "events": The list of operation events recorded during the process.
        
        The method logs an UPDATED event if any directories or files were renamed, a SKIPPED event if no changes were required, or a FAILED event if an error occurs (in which case the exception is re-raised).
        """
        try:
            dirs_renamed = self.rename_directories()
            files_renamed = self.rename_files()

            if dirs_renamed or files_renamed:
                self.events.append(
                    OperationEvent(
                        kind=EventKind.UPDATED,
                        target="repository_structure",
                        data={
                            "directories_renamed": dirs_renamed,
                            "files_renamed": files_renamed,
                        },
                    )
                )
            else:
                self.events.append(
                    OperationEvent(
                        kind=EventKind.SKIPPED,
                        target="repository_structure",
                        data={"reason": "no_changes_required"},
                    )
                )
            return {
                "result": {
                    "directories_renamed": dirs_renamed,
                    "files_renamed": files_renamed,
                },
                "events": self.events,
            }
        except Exception as e:
            self.events.append(
                OperationEvent(
                    kind=EventKind.FAILED,
                    target="repository_structure",
                    data={"error": str(e)},
                )
            )
            raise

    def rename_directories(self) -> int:
        """
        Translates directory names into English and updates code to reflect changes.
        
        This method orchestrates the renaming of directories within the repository to their English-translated equivalents. It ensures that any references to these directories within Python source files are also updated to maintain code consistency. The process is performed in a safe, conflict-aware manner, avoiding overwrites of existing paths.
        
        Args:
            None
        
        Returns:
            int: The number of directories successfully renamed.
        
        Why:
            Renaming directories to English standardizes the repository structure, improving accessibility and maintainability, especially for international contributors. Updating code references prevents broken imports and ensures the repository remains functional after structural changes.
        """
        logger.info("Starting directory renaming process...")

        renamed = 0
        all_dirs = self._get_all_directories()
        rename_map = self.translate_directories(all_dirs)

        self._cycle_update_code(rename_map)

        # Rename directories
        try:
            for old_path in reversed(all_dirs):
                old_name = os.path.basename(old_path)
                if old_name in rename_map:
                    new_name = rename_map[old_name]
                    new_path = os.path.join(os.path.dirname(old_path), new_name)
                    os.rename(old_path, new_path)
                    renamed += 1
                    logger.info(f'Renamed: "{old_name}" → "{new_name}"')
        except Exception as e:
            logger.error("Error while renaming directories: %s", e, exc_info=True)

        logger.info("Directory renaming completed successfully")
        return renamed

    def rename_files(self) -> int:
        """
        Translates all file names into English, preserving their extensions.
        
        This method iterates through all files in the repository, translates their base names (without extensions) into English, and renames the files accordingly. It also updates any internal code references to the renamed files to maintain consistency.
        
        Args:
            None
        
        Returns:
            The number of files successfully renamed.
        
        Why:
            Renaming files to English improves accessibility and maintainability, especially for international contributors. The method ensures that file extensions remain unchanged and that any code referencing the files is updated to prevent broken links or import errors.
        """
        logger.info("Starting files renaming process...")
        renamed = 0
        all_files = self._get_all_files()
        rename_map, rename_map_code = self.translate_files(all_files)
        self._cycle_update_code(rename_map_code)

        try:
            for old_path, new_path in rename_map.items():
                os.rename(old_path, new_path)
                renamed += 1
                _, old_name = os.path.split(os.path.basename(old_path))
                _, new_name = os.path.split(os.path.basename(new_path))
                logger.info(f'Renamed: "{old_name}" → "{new_name}"')
        except Exception as e:
            logger.error("Error while renaming files: %s", e, exc_info=True)

        logger.info("Files renaming completed successfully")
        return renamed

    def translate_directories(self, all_dirs) -> dict:
        """
        Generates a mapping of directory names to their translated versions.
        
        Iterates through a list of directory paths, translates each directory's
        basename, and creates a mapping from the original name to the new name
        if the translation results in a different name and the new path does not
        already exist. The base path is skipped.
        
        WHY: This method supports repository internationalization or standardization
        by renaming directories to translated versions, while avoiding conflicts with
        existing paths and preserving the base directory structure.
        
        Args:
            all_dirs: A list of directory paths to process.
        
        Returns:
            A dictionary where keys are original directory names and values are
            their translated names. Only includes entries where the name changed
            and the new path does not already exist.
        """
        rename_map = {}
        try:
            for old_path in all_dirs:
                if old_path == self.base_path:
                    continue

                dirname = os.path.basename(old_path)
                translated_name = self._translate_text(dirname)
                new_path = os.path.join(os.path.dirname(old_path), translated_name)

                if old_path != new_path and not os.path.exists(new_path):
                    rename_map[dirname] = translated_name

            logger.info(f"Finished generating new names for {len(rename_map)} directories")
        except Exception as e:
            logger.error("Error while generating new names for directories: %s", e, exc_info=True)
        return rename_map

    def translate_files(self, all_files) -> tuple[dict, dict]:
        """
        Translates file names in a given list, generating rename mappings.
        
        This method processes each file path in the provided list, translates the base filename
        (without extension) using an internal translation function, and constructs a new path.
        It produces two dictionaries: one mapping original full paths to new full paths for
        actual file renaming, and another mapping original filenames (with extensions for
        non-code files) to translated filenames for code reference updates.
        
        WHY two maps are needed:
        - rename_map is used for the physical file system renaming operation.
        - rename_map_code is used to update textual references (e.g., import statements) within source code files. Extensions are preserved for non-code files so references remain valid.
        
        Args:
            all_files: A list of file paths to be processed for name translation.
        
        Returns:
            A tuple containing two dictionaries:
                rename_map: Maps original full file paths to new full file paths. A mapping is only added if the new path differs from the old path and does not already exist on the filesystem.
                rename_map_code: Maps original filenames to translated filenames for code updates. For files not considered code (based on self.extensions_code_files), the extension is included in both the key and value.
        
        Note:
            The method logs an info message upon successful completion and logs an error with traceback if an exception occurs.
        """
        rename_map = {}
        rename_map_code = {}
        try:
            for old_path in all_files:
                dirname = os.path.dirname(old_path)
                filename, extension = os.path.splitext(os.path.basename(old_path))

                translated_name = self._translate_text(filename)
                new_path = os.path.join(dirname, translated_name + extension)

                if old_path != new_path and not os.path.exists(new_path):
                    rename_map[old_path] = new_path

                    if extension not in self.extensions_code_files:
                        filename += extension
                        translated_name += extension

                    rename_map_code[filename] = translated_name

            logger.info(f"Finished generating new names for {len(rename_map)} files")
        except Exception as e:
            logger.error("Error while generating new names for files: %s", e, exc_info=True)

        return rename_map, rename_map_code

    def _translate_text(self, text: str) -> str:
        """
        Translation of directory or file name into English via LLM.
        
        This method sends a query to the language model (LLM) to translate the given text into English.
        It first checks if the text is in an excluded list; if so, the original text is returned unchanged.
        Otherwise, a prompt instructs the LLM to translate only meaningful names, leaving default or special system names unchanged.
        The response is then processed: spaces are replaced with underscores, and the result is lowercased.
        If the LLM returns an empty response, the original text is returned.
        
        Args:
            text: The original directory or file name to translate.
        
        Returns:
            The translated text with spaces replaced by underscores and lowercased, or the original text if excluded or if translation fails.
        """
        if text.lower() in self.excluded_names:
            return text

        prompt = (
            "You are translating file or directory names into English.\n"
            "Rules:\n"
            "- If the name is a default file name or a special system/hidden file (like __init__, .gitignore, README), return it unchanged.\n"
            "- Only translate meaningful names.\n"
            "- Output only the translated name.\n"
            "- Replace spaces with underscores.\n"
            "- Lowercase the result.\n"
            "- Do not add explanations or extra text.\n\n"
            f"Input name: {text}\n"
            "Output:"
        )
        response = self.model_handler.send_request(prompt)

        return response.replace(" ", "_") if response else text

    def _get_all_files(self) -> list[str]:
        """
        Recursively collects a list of all files in a project, excluding certain directories.
        
        Why: This method provides a comprehensive inventory of all files in the repository,
        which is necessary for subsequent analysis, documentation generation, and structural
        enhancements performed by the OSA Tool.
        
        Args:
            self: The instance of RepositoryStructureTranslator.
            No explicit parameters are passed; the method uses instance attributes.
        
        Returns:
            list[str]: List of absolute paths to all found files within the repository's
            base path, excluding any directories specified in `self.excluded_dirs`.
        """
        all_files = []

        try:
            for root, _, files in os.walk(self.base_path):
                if any(excluded in root for excluded in self.excluded_dirs):
                    continue

                all_files.extend(os.path.join(root, file) for file in files)

            logger.info(f"Collected {len(all_files)} files in repository")
        except Exception as e:
            logger.error("Error while searching repository files: %s", e, exc_info=True)

        return all_files

    def _get_all_directories(self) -> list[str]:
        """
        Recursively collects a list of all directories in a project, excluding certain directories.
        
        The method walks through the repository's file system to build a comprehensive list of directory paths. This is used to understand the project's structure for subsequent documentation and analysis operations.
        
        Args:
            self.base_path: The root directory of the repository from which the search begins.
            self.excluded_dirs: A list of directory names to exclude from the collection (e.g., '.git', '__pycache__').
        
        Returns:
            list[str]: A list of full paths to all directories found, excluding the specified ones. Returns an empty list if an error occurs during traversal.
        
        Why:
            A complete directory list is necessary for tasks like mapping the repository structure, generating navigation aids, or applying transformations only to relevant parts of the codebase. Excluding certain directories (like version control or cache folders) prevents noise and focuses analysis on the actual source code and documentation.
        """
        all_dirs = []

        try:
            for root, dirs, _ in os.walk(self.base_path, topdown=True):
                dirs[:] = [d for d in dirs if d not in self.excluded_dirs]

                all_dirs.extend(os.path.join(root, dirname) for dirname in dirs)

            logger.info(f"Finished collecting all directories of repository ({len(all_dirs)} found)")
        except Exception as e:
            logger.error("Error: %s", e, exc_info=True)

        return all_dirs

    @staticmethod
    def update_code(file_path: str, rename_map: dict) -> None:
        """
        Updates imported modules and paths in the file, replacing old names with new ones.
        
        The function opens the file at the specified path, reads its contents,
        and replaces the names of imported modules and paths according to the `rename_map` dictionary.
        If changes were made, the file is overwritten.
        
        This is used to automatically update code references when renaming modules or directories in a repository,
        ensuring that imports and file paths remain consistent after structural changes.
        
        Args:
            file_path: Path to the file in which imports and paths need to be updated.
            rename_map: Dictionary of {old_name:new_name} matches for replacement.
                Keys are old module or directory names; values are the new names to substitute.
        
        Behavior:
        1. Processes Python import statements (both `import` and `from ... import` forms) and updates module names.
        2. Updates path strings inside quotes (both single and double) by replacing directory or file name components.
        3. Updates path arguments in common file and path operations (e.g., `os.path.join`, `open`, `Path`, `shutil.copy`, `pandas.read_csv`, `torch.load`).
           This ensures that string arguments passed to these functions are also renamed appropriately.
        4. Only writes back to the file if any changes were detected, preserving original modification dates when no updates are needed.
        5. Logs an info message on successful update or an error if the operation fails.
        
        Returns: None
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            updated_content = content

            # Processes imports
            def replace_imports(match):
                keyword, module, alias = match.groups()
                module_parts = module.split(".")
                updated_parts = [rename_map.get(part, part) for part in module_parts]
                updated_module = ".".join(updated_parts)
                return f"{keyword} {updated_module}{alias or ''}"

            updated_content = re.sub(
                r"\b(import|from)\s+([\w.]+)(\s+as\s+\w+)?",
                replace_imports,
                updated_content,
            )

            # Update names in strings
            string_pattern = r"(['\"])(.*?)\1"

            def replace_in_strings(match):
                quote, path = match.groups()
                parts = re.split(r"[/\\]", path)
                updated_parts = [rename_map.get(part, part) for part in parts]
                return f"{quote}{'/'.join(updated_parts)}{quote}"

            # Regular expression for finding string arguments in functions
            path_patterns = [
                r"(os\.path\.join\()([^)]+)(\))",
                r"(os\.path\.abspath\()([^)]+)(\))",
                r"(os\.path\.dirname\()([^)]+)(\))",
                r"(Path\()([^)]+)(\))",
                r"(open\()([^)]+)(\))",
                r"([a-zA-Z_]*\.read_csv\()([^)]+)(\))",
                r"([a-zA-Z_]*\.to_csv\()([^)]+)(\))",
                r"(shutil\.copy\()([^)]+)(\))",
                r"(shutil\.move\()([^)]+)(\))",
                r"(glob\.glob\()([^)]+)(\))",
                r"(json\.load\()([^)]+)(\))",
                r"(pickle\.load\()([^)]+)(\))",
                r"(torch\.load\()([^)]+)(\))",
            ]

            def replace_names(match):
                prefix, args, suffix = match.groups()
                args = re.sub(string_pattern, replace_in_strings, args)
                return f"{prefix}{args}{suffix}"

            updated_content = re.sub(string_pattern, replace_in_strings, updated_content)
            for pattern in path_patterns:
                updated_content = re.sub(pattern, replace_names, updated_content)

            if updated_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                logger.info(f"Updated imports and paths in: {file_path}")
        except Exception as e:
            logger.error(f"Failed to update {file_path}", repr(e), exc_info=True)

    def _cycle_update_code(self, rename_map: dict) -> None:
        """
        Updates Python files by applying a rename mapping to each file.
        
        Args:
            rename_map: A dictionary mapping old names to new names for renaming within the code.
        
        This method processes all Python files in the repository, applying the rename mapping to each file.
        It is part of a cycle that iteratively updates code to reflect structural or naming changes in the repository.
        The method does not initialize any instance attributes.
        """
        python_files = [file for file in self._get_all_files() if file.endswith(".py")]
        for file in python_files:
            self.update_code(file, rename_map)
