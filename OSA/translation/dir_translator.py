import os

from typing import Union

from readmeai.config.settings import ConfigLoader
from readmeai.readmegen_article.config.settings import ArticleConfigLoader

from OSA.utils import parse_folder_name
from OSA.osatreesitter.models import ModelHandlerFactory, ModelHandler


class DirectoryTranslator:
    def __init__(
            self,
            config_loader: Union[ConfigLoader, ArticleConfigLoader]
    ):
        self.config = config_loader.config
        self.repo_url = self.config.git.repository
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)

    def translate_text(self, text: str) -> str:
        """Translation of directory name into English via LLM"""
        prompt = (f"Translate into English text: {text}\n"
                  f"Return only the answer.")
        response = self.model_handler.send_request(prompt)
        return response.replace(" ", "_")

    def get_python_files(self):
        """Recursive search of all Python files in a project"""
        python_files = []
        base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

        for root, _, files in os.walk(base_path):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        return python_files

    def rename_directories(self) -> None:
        """
        Translates directory names into English
        and updates code to reflect changes.
        """
        exclude_dirs = {".git", ".venv"}
        rename_map = {}  # Storage of old and new names

        base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

        # Collect all directories (sort from deepest to top)
        all_dirs = []
        for root, dirs, _ in os.walk(base_path, topdown=True):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]

            for dirname in dirs:
                old_path = os.path.join(root, dirname)
                all_dirs.append(old_path)

        # Generate new names
        for old_path in all_dirs:
            if old_path == base_path:
                continue

            dirname = os.path.basename(old_path)
            translated_name = self.translate_text(dirname)
            new_path = os.path.join(os.path.dirname(old_path), translated_name)

            if old_path != new_path and not os.path.exists(new_path):
                rename_map[dirname] = translated_name
        print(rename_map)
        for old_path in reversed(all_dirs):
            old_name = os.path.basename(old_path)
            if old_name in rename_map:
                new_name = rename_map[old_name]
                new_path = os.path.join(os.path.dirname(old_path), new_name)
                os.rename(old_path, new_path)
                print(f'Renamed: "{old_name}" → "{new_name}"')
