import os
import json
from pathlib import Path
from typing import Dict, List, Any

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptLoader, PromptBuilder
from osa_tool.utils.utils import parse_folder_name


class RepoOrganizer:
    """
    A class to analyze and reorganize repository structure using AI models.
    """
    
    def __init__(self, config_loader: ConfigLoader, prompts: PromptLoader):
        """
        Initializes the RepoOrganizer with configuration and prompts.

        Args:
            config_loader: Loader for configuration settings
            prompts: Loader for prompt templates
        """
        self.config = config_loader.config
        self.prompts = prompts
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

    def get_repo_structure(self) -> str:
        """
        Generates a complete tree representation of the entire repository structure.

        Returns:
            str: A formatted string showing the complete directory tree with all files.
        """
        tree_structure = []
        base_path_obj = Path(self.base_path)

        def build_tree(path: Path, prefix: str = "", is_last: bool = True):
            """
            Recursively builds complete directory tree structure.
            
            Args:
                path: Current directory path
                prefix: Prefix for visual indentation
                is_last: Whether this is the last item in parent directory
            """
            items = [item for item in sorted(path.iterdir()) if not item.name.startswith('.')]
            files = [item for item in items if item.is_file()]
            dirs = [item for item in items if item.is_dir()]

            connector = "└── " if is_last else "├── "
            if path == base_path_obj:
                dir_name = parse_folder_name(self.repo_url)
                tree_structure.append(f"{connector} {dir_name}/")
            else:
                tree_structure.append(f"{prefix}{connector} {path.name}/")

            new_prefix = prefix + ("    " if is_last else "│   ")

            for i, file_path in enumerate(files):
                file_is_last = (i == len(files) - 1) and (not dirs)
                file_connector = "└── " if file_is_last else "├── "
                tree_structure.append(f"{new_prefix}{file_connector} {file_path.name}")

            for i, directory in enumerate(dirs):
                dir_is_last = (i == len(dirs) - 1)
                build_tree(directory, new_prefix, dir_is_last)

        build_tree(base_path_obj, "", True)
        
        return "\n".join(tree_structure)

    def generate_reorganization_plan(self) -> Dict[str, Any]:
        """
        Generates a reorganization plan for the repository using AI model.

        Returns:
            Dict[str, Any]: A JSON object containing the reorganization plan with 
                           actions to be performed on the repository.

        Raises:
            Exception: If the AI model fails to generate a valid plan or 
                      if the response cannot be parsed as JSON.
        """
        tree_structure = self.get_repo_structure()
        
        prompt = PromptBuilder.render(
            self.prompts.get("repo_reorganization"),
            tree_structure=tree_structure,
        )

        try:
            response = self.model_handler.send_request(prompt)
            logger.debug(f"Model response: {response}")
            return json.loads(response)
        except Exception as e:
            logger.error(f"Error generating reorganization plan: {e}")
            raise

    def execute_reorganization(self, plan: Dict[str, Any]):
        """
        Executes the reorganization plan by performing all specified actions.

        Args:
            plan: Dictionary containing the reorganization plan with actions to execute.
        """
        actions = plan.get("actions", [])
        
        for action in actions:
            try:
                action_type = action["type"]
                if action_type == "create_directory":
                    self._create_directory(action["path"])
                elif action_type == "move_file":
                    self._move_file(action["source"], action["destination"])
                elif action_type == "delete_file":
                    self._delete_file(action["path"])
                elif action_type == "update_content":
                    self._update_content(action["path"], action["content"])
                else:
                    logger.warning(f"Unknown action type: {action_type}")
            except Exception as e:
                logger.error(f"Error executing action {action}: {e}")

    def _create_directory(self, path: str):
        """
        Creates a directory at the specified path.

        Args:
            path: Relative path where the directory should be created.
        """
        full_path = os.path.join(self.base_path, path)
        os.makedirs(full_path, exist_ok=True)
        logger.info(f"Created directory: {path}")

    def _move_file(self, source: str, destination: str):
        """
        Moves a file from source to destination path.

        Args:
            source: Relative path to the source file.
            destination: Relative path to the destination location.
        """
        source_path = os.path.join(self.base_path, source)
        dest_path = os.path.join(self.base_path, destination)
        
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        os.rename(source_path, dest_path)
        logger.info(f"Moved file: {source} -> {destination}")

    def _delete_file(self, path: str):
        """
        Deletes a file at the specified path.

        Args:
            path: Relative path to the file to be deleted.
        """
        full_path = os.path.join(self.base_path, path)
        os.remove(full_path)
        logger.info(f"Deleted file: {path}")

    def _update_content(self, path: str, content: str):
        """
        Updates the content of a file.

        Args:
            path: Relative path to the file to be updated.
            content: New content to write to the file.
        """
        full_path = os.path.join(self.base_path, path)
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Updated file: {path}")

    def reorganize(self):
        """
        Main method to perform complete repository reorganization.
        
        Executes the following steps:
        1. Analyzes current repository structure
        2. Generates reorganization plan using AI model
        3. Executes the generated plan
        """
        logger.info("Starting repository structure analysis...")
        tree_structure = self.get_repo_structure()
        logger.debug(f"Repository structure:\n{tree_structure}")

        logger.info("Generating reorganization plan...")
        plan = self.generate_reorganization_plan()

        logger.info("Executing reorganization plan...")
        self.execute_reorganization(plan)
        logger.info("Repository reorganization completed!")
