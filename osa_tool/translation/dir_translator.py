import os
import re

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.utils import logger, parse_folder_name


class DirectoryTranslator:
    """
    DirectoryTranslator
    
    The DirectoryTranslator class provides utilities to translate directory and file names in a repository into English, update import paths accordingly, and manage file renaming while preserving code integrity. It uses an LLM for translation and handles exclusion rules for directories and file names.
    
    Methods:
    - __init__
    - _translate_text
    - _get_python_files
    - _get_all_files
    - _get_all_directories
    - update_code
    - _cycle_update_code
    - translate_directories
    - translate_files
    - rename_files
    - rename_directories
    - rename_directories_and_files
    
    Attributes:
    - config
    - repo_url
    - model_handler
    - base_path
    - excluded_dirs
    - extensions_code_files
    - excluded_names
    """
    def __init__(self, config_loader: ConfigLoader):
        """
        Initializes the repository analyzer with configuration and sets up default parameters.
        
        Args:
            config_loader: A ConfigLoader instance that provides the application settings.
        
        Attributes:
            config: The configuration object extracted from the provided ConfigLoader.
            repo_url: The Git repository URL obtained from the configuration.
            model_handler: A ModelHandler instance created by ModelHandlerFactory.build using the configuration.
            base_path: The absolute path to the repository directory, constructed by joining the current working directory with the parsed folder name from the repository URL.
            excluded_dirs: A set of directory names that should be ignored during analysis (e.g., ".git", ".venv").
            extensions_code_files: A set of file extensions considered as code files (currently only ".py").
            excluded_names: A set of file or directory names that should be excluded from processing (e.g., "main", "LICENSE", "README", "requirements", "examples", "docs").
        
        Returns:
            None
        """
        self.config = config_loader.config
        self.repo_url = self.config.git.repository
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

        self.excluded_dirs = {".git", ".venv"}
        self.extensions_code_files = {".py"}
        self.excluded_names = {
            "main",
            "LICENSE",
            "README",
            "requirements",
            "examples",
            "docs",
        }

    def _translate_text(self, text: str) -> str:
        """
        Translation of directory name into English via LLM

        The function sends a query to the language model (`LLM`),
        asking for a translation of the passed text into English.
        In the response, it leaves only the translated text and replaces spaces with underscores.

        Arguments:
            text (str): The original text to translate.

        Returns:
            response: The translated text, with spaces replaced by `_`.
        """
        if text in self.excluded_names:
            return text

        prompt = f"Translate into English text: {text} and save every word here.\n" f"Return only the answer."
        response = self.model_handler.send_request(prompt)
        return response.replace(" ", "_")

    def _get_python_files(self) -> list[str]:
        """
        Recursive search of all Python files in a project

        The function scans the project folder (defined by the repository URL),
        recursively goes through all subdirectories and collects paths to `.py` files.

        Returns:
            list[str]: List of absolute paths to all found Python files.
        """
        python_files = []
        try:
            for root, _, files in os.walk(self.base_path):
                for file in files:
                    if file.endswith(".py"):
                        python_files.append(os.path.join(root, file))

            logger.info(f"Collected {len(python_files)} Python files")
        except Exception as e:
            logger.error("Error while searching Python files, %s", e, exc_info=True)

        return python_files

    def _get_all_files(self) -> list[str]:
        """
        Recursively collects a list of all files in a project, excluding certain directories.

        Returns:
            list[str]: List of paths to all found files
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

        Returns:
            list[str]: List of paths to all found files
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

        The function opens the file at the specified path, reads its contents
        and replaces the names of imported modules and paths according to the `rename_map` dictionary.
        If changes were made, the file is overwritten.

        Args:
            file_path: Path to the file in which imports and paths need to be updated.
            rename_map: Dictionary of {old_name:new_name} matches for replacement.

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
        Updates the code in all Python files within the repository using the provided rename map.
        
        This method retrieves all Python files via the internal `_get_python_files` helper and then applies the
        `update_code` operation to each file, passing along the `rename_map` which specifies the substitutions
        to perform.
        
        Args:
            rename_map: A dictionary mapping identifiers or strings to be replaced in the code to their
                corresponding new values.
        
        Returns:
            None
        """
        python_files = self._get_python_files()
        for file in python_files:
            self.update_code(file, rename_map)

    def translate_directories(self, all_dirs) -> dict:
        """
        Translate directory names within a given list of paths.
        
        This method iterates over a collection of directory paths, translating each
        directory name using the instance's `_translate_text` helper. It skips the
        repository's base path and avoids generating a new name if the translated
        name already exists. The resulting mapping of original directory names to
        their translated counterparts is returned.
        
        Args:
            all_dirs: A sequence of absolute directory paths to be processed.
        
        Returns:
            A dictionary mapping each original directory name (basename of the path)
            to its translated name. Only entries for directories that will actually
            be renamed are included.
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
        Translate file names and generate rename mappings.
        
        This method iterates over a collection of file paths, translating each file name
        using the instance's `_translate_text` method. It builds two dictionaries:
        
        * `rename_map` – maps original file paths to their new translated paths.
        * `rename_map_code` – maps original file names (including extension for code
          files) to the translated names.
        
        The method skips files that would not change name or would overwrite an
        existing file. For files whose extensions are not listed in
        `self.extensions_code_files`, the extension is appended to the key and value
        in `rename_map_code` to preserve the full file name.
        
        Parameters
        ----------
        all_files : Iterable[str]
            A sequence of file paths to be processed.
        
        Returns
        -------
        tuple[dict, dict]
            A tuple containing two dictionaries:
            1. `rename_map`: mapping from original file paths to new translated paths.
            2. `rename_map_code`: mapping from original file names (with extension for
               code files) to translated names.
        
        Notes
        -----
        * The method logs the number of files renamed and any errors encountered.
        * It relies on the instance attributes `self._translate_text` and
          `self.extensions_code_files` for name translation and file type checks.
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

    def rename_files(self) -> None:
        """
        Translates all file names into English, preserving their extensions.
        """
        logger.info("Starting files renaming process...")

        all_files = self._get_all_files()
        rename_map, rename_map_code = self.translate_files(all_files)
        self._cycle_update_code(rename_map_code)

        try:
            for old_path, new_path in rename_map.items():
                os.rename(old_path, new_path)

                _, old_name = os.path.split(os.path.basename(old_path))
                _, new_name = os.path.split(os.path.basename(new_path))
                logger.info(f'Renamed: "{old_name}" → "{new_name}"')
        except Exception as e:
            logger.error("Error while renaming files: %s", e, exc_info=True)

        logger.info("Files renaming completed successfully")

    def rename_directories(self) -> None:
        """
        Translates directory names into English
        and updates code to reflect changes.
        """
        logger.info("Starting directory renaming process...")

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
                    logger.info(f'Renamed: "{old_name}" → "{new_name}"')
        except Exception as e:
            logger.error("Error while renaming directories: %s", e, exc_info=True)

        logger.info("Directory renaming completed successfully")

    def rename_directories_and_files(self) -> None:
        """
        The complete process of translating directories and files in the repository.
        """
        self.rename_directories()
        self.rename_files()
