import os
import logging
import re

from rich.logging import RichHandler
from typing import Union, List

from readmeai.config.settings import ConfigLoader
from readmeai.readmegen_article.config.settings import ArticleConfigLoader

from OSA.utils import parse_folder_name
from OSA.osatreesitter.models import ModelHandlerFactory, ModelHandler

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

logger = logging.getLogger("rich")


class DirectoryTranslator:
    def __init__(
            self,
            config_loader: Union[ConfigLoader, ArticleConfigLoader]
    ):
        self.config = config_loader.config
        self.repo_url = self.config.git.repository
        self.model_handler: ModelHandler = ModelHandlerFactory.build(
            self.config)

    def translate_text(self, text: str) -> str:
        """
        Translation of directory name into English via LLM

        The function sends a query to the language model (`LLM`),
        asking for a translation of the passed text into English.
        In the response, it leaves only the translated text and replaces spaces with underscores.

        Arguments:
            text (str): The original text to translate.

        Returns:
            str: The translated text, with spaces replaced by `_`.
        """
        prompt = (f"Translate into English text: {text}\n"
                  f"Return only the answer.")
        response = self.model_handler.send_request(prompt)
        return response.replace(" ", "_")

    def get_python_files(self) -> List:
        """
        Recursive search of all Python files in a project

        The function scans the project folder (defined by the repository URL),
        recursively goes through all subdirectories and collects paths to `.py` files.

        Returns:
            List[str]: List of absolute paths to all found Python files.
        """
        python_files = []
        base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        try:
            for root, _, files in os.walk(base_path):
                for file in files:
                    if file.endswith(".py"):
                        python_files.append(os.path.join(root, file))

            logger.info(
                f"Collected {len(python_files)} Python files")
        except Exception as e:
            logger.error("Error while searching Python files, %s", e,
                         exc_info=True)

        return python_files



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

        Returns:

        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            updated_content = content

            # Processes imports
            def replace_imports(match):
                words = re.split(r'(\W+)', match.group(0))
                return ''.join([rename_map.get(w, w) for w in words])

            updated_content = re.sub(
                r'\b(import\s+[\w.]+|from\s+[\w.]+\s+import)',
                replace_imports,
                updated_content
            )

            def replace_path_elements(match):
                path_str = match.group(1)
                parts = re.split(r'([/,])', path_str)
                updated_parts = [
                    '"{}"'.format(rename_map.get(p.strip("\"' "), p))
                    if p.strip("\"' ").isidentifier() else p
                    for p in parts
                ]
                return match.group(0).replace(path_str, ''.join(updated_parts))

            def replace_os_path_join(match):
                args = match.group(1)
                parts = re.split(r'(\s*,\s*)', args)
                updated_parts = [
                    '"{}"'.format(rename_map.get(p.strip("\"' "), p))
                    if p.strip("\"' ").isidentifier() else p
                    for p in parts
                ]
                return f'os.path.join({"".join(updated_parts)})'

            def replace_pathlib_path(match):
                path_parts = match.group(0).split(" / ")
                updated_parts = [
                    '"{}"'.format(rename_map.get(p.strip("\"' "), p))
                    if p.strip("\"' ").isidentifier() else p
                    for p in path_parts
                ]
                return " / ".join(updated_parts)

            path_patterns = [
                (r'os\.path\.join\(([^)]+)\)', replace_os_path_join),
                (r'Path\(["\']([^"\']+)["\']\)', replace_path_elements),
                (r'open\(["\']([^"\']+)/', replace_path_elements),
                (r'Path\(["\'][^"\']+["\']\)\s*(/\s*["\'][^"\']+["\'])*', replace_pathlib_path)
            ]

            for pattern, repl in path_patterns:
                updated_content = re.sub(pattern, repl, updated_content)

            if updated_content != content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(updated_content)
                logger.info(f"Updated imports and paths in: {file_path}")
        except Exception as e:
            logger.error(f"Failed to update {file_path}", repr(e), exc_info=True)

    def rename_directories(self) -> None:
        """
        Translates directory names into English
        and updates code to reflect changes.
        """
        logger.info("Starting directory renaming process...")
        exclude_dirs = {".git", ".venv"}
        rename_map = {}  # Storage of old and new names

        base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

        # Collect all directories
        all_dirs = []
        try:
            for root, dirs, _ in os.walk(base_path, topdown=True):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]

                for dirname in dirs:
                    old_path = os.path.join(root, dirname)
                    all_dirs.append(old_path)

            logger.info(f"Finished collecting all directories of repository ({len(all_dirs)} found)")
        except Exception as e:
            logger.error("Error: %s", e, exc_info=True)

        # Generate new names
        try:
            for old_path in all_dirs:
                if old_path == base_path:
                    continue

                dirname = os.path.basename(old_path)
                translated_name = self.translate_text(dirname)
                new_path = os.path.join(os.path.dirname(old_path),
                                        translated_name)

                if old_path != new_path and not os.path.exists(new_path):
                    rename_map[dirname] = translated_name

            logger.info(f"Finished generating new names for {len(rename_map)} directories")
        except Exception as e:
            logger.error(
                "Error while generating new names for directories: %s",
                e, exc_info=True)

        python_files = self.get_python_files()
        for file in python_files:
            self.update_code(file, rename_map)

        # Rename directories
        try:
            for old_path in reversed(all_dirs):
                old_name = os.path.basename(old_path)
                if old_name in rename_map:
                    new_name = rename_map[old_name]
                    new_path = os.path.join(os.path.dirname(old_path),
                                            new_name)
                    os.rename(old_path, new_path)
                    logger.info(f'Renamed: "{old_name}" → "{new_name}"')
        except Exception as e:
            logger.error("Error while renaming directories: %s", e,
                         exc_info=True)

        logger.info("Directory renaming completed successfully")
