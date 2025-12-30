import os
import json
import shutil
import re
import ast
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptLoader, PromptBuilder
from osa_tool.utils.utils import parse_folder_name


class ImportAnalyzer:
    """
    Analyzes and manages import dependencies in Python projects.

    Tracks which files import from which modules and updates imports
    when files are moved within the repository structure.
    """

    def __init__(self, base_path: str):
        """
        Initializes the ImportAnalyzer with the repository base path.

        Args:
            base_path: The absolute path to the root of the repository.
        """
        self.base_path = base_path
        self.import_map: Dict[str, Set[str]] = {}
        self.python_files: List[str] = []
        self.moved_files: Dict[str, str] = {}

    def discover_python_files(self) -> List[str]:
        """
        Discovers all Python files within the repository.

        Walks through all directories excluding hidden ones and collects
        all files with .py extension.

        Returns:
            List[str]: List of relative paths to Python files from the base path.
        """
        self.python_files = []
        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.base_path)
                    self.python_files.append(rel_path)
        return self.python_files

    def extract_imports(self, file_path: str) -> Set[str]:
        """
        Extracts import statements from a Python file using AST parsing.

        Args:
            file_path: Relative path to the Python file from the base path.

        Returns:
            Set[str]: Set of imported module names (first component only).
        """
        full_path = os.path.join(self.base_path, file_path)
        imports = set()
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])
        except Exception as e:
            logger.warning(f"Could not parse imports in {file_path}: {e}")
        
        return imports

    def build_import_map(self) -> Dict[str, Set[str]]:
        """
        Builds a dependency map between modules and files that import them.

        Returns:
            Dict[str, Set[str]]: Dictionary mapping module names to sets of files that import them.
        """
        self.discover_python_files()
        self.import_map.clear()
        
        for py_file in self.python_files:
            imports = self.extract_imports(py_file)
            for imp in imports:
                if imp not in self.import_map:
                    self.import_map[imp] = set()
                self.import_map[imp].add(py_file)
        
        return self.import_map

    def get_files_importing_module(self, module_path: str) -> Set[str]:
        """
        Retrieves all files that import a specific module.

        Args:
            module_path: Relative path to the module file.

        Returns:
            Set[str]: Set of file paths that import the specified module.
        """
        module_key = module_path.replace('.py', '').replace('/', '.')
        
        importing_files = set()
        for imp_module, files in self.import_map.items():
            if module_key in imp_module or imp_module in module_key:
                importing_files.update(files)
        
        return importing_files

    def _resolve_current_path(self, path: str) -> str:
        """
        Resolves a file path considering previous move operations.

        Args:
            path: Original path of the file.

        Returns:
            str: Current path of the file after any moves.
        """
        if path in self.moved_files:
            return self.moved_files[path]
        return path

    def update_imports_in_file(self, file_path: str, old_import: str, new_import: str) -> str:
        """
        Updates import statements in a file after module relocation.

        Args:
            file_path: Path to the file containing imports to update.
            old_import: Original import path of the moved module.
            new_import: New import path after relocation.

        Returns:
            str: Updated file content, or None if update failed.
        """
        actual_path = self._resolve_current_path(file_path)
        full_path = os.path.join(self.base_path, actual_path)
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            from_pattern = rf'from\s+{re.escape(old_import)}\s+import'
            content = re.sub(from_pattern, f'from {new_import} import', content)
            
            import_pattern = rf'import\s+{re.escape(old_import)}(\s|$|,)'
            content = re.sub(import_pattern, f'import {new_import}\\1', content)
            
            return content
        except Exception as e:
            logger.warning(f"Could not update imports in {file_path}: {e}")
            return None


class StructureQualityValidator:
    """
    Evaluates the quality of repository structure organization.

    Provides quantitative scoring and issue detection for repository
    layout based on established software engineering conventions.
    """

    def __init__(self, base_path: str):
        """
        Initializes the validator with the repository base path.

        Args:
            base_path: Absolute path to the repository root.
        """
        self.base_path = base_path
        self.quality_score = 0.0
        self.issues = []

    def validate_structure(self) -> Tuple[float, List[str]]:
        """
        Performs comprehensive structure quality assessment.

        Returns:
            Tuple[float, List[str]]: Quality score (0-100) and list of identified issues.
        """
        self.quality_score = 100.0
        self.issues = []
        
        self._check_directory_depth()
        self._check_scattered_files()
        self._check_naming_conventions()
        self._check_module_organization()
        self._check_duplication()
        self._check_missing_init_files()
        
        return self.quality_score, self.issues

    def _check_directory_depth(self):
        """
        Validates that directory nesting depth is within reasonable bounds.
        """
        max_depth = 0
        for root, dirs, files in os.walk(self.base_path):
            depth = root.replace(self.base_path, '').count(os.sep)
            max_depth = max(max_depth, depth)
        
        if max_depth > 8:
            self.quality_score -= 10
            self.issues.append(f"Directory structure is too deep ({max_depth} levels)")
        elif max_depth < 2:
            self.quality_score -= 5
            self.issues.append("Directory structure is too flat")

    def _check_scattered_files(self):
        """
        Detects excessive number of source files at repository root level.
        """
        root_items = os.listdir(self.base_path)
        root_files = [f for f in root_items if os.path.isfile(os.path.join(self.base_path, f))]
        
        exclude_patterns = {'.gitignore', 'README.md', 'setup.py', 'requirements.txt',
                          'LICENSE', 'Makefile', 'pyproject.toml', '.env'}
        source_files = [f for f in root_files if not any(f.endswith(p) for p in exclude_patterns)]
        
        if len(source_files) > 5:
            self.quality_score -= 15
            self.issues.append(f"Too many source files at root level ({len(source_files)})")

    def _check_naming_conventions(self):
        """
        Checks compliance with common file naming conventions.
        """
        issues_found = 0
        
        for root, dirs, files in os.walk(self.base_path):
            for name in dirs + files:
                if ' ' in name:
                    issues_found += 1
                if name.endswith('.py') and not name.replace('_', '').replace('.py', '').islower():
                    issues_found += 1
        
        if issues_found > 10:
            self.quality_score -= 10
            self.issues.append(f"Inconsistent naming conventions detected ({issues_found} issues)")

    def _check_module_organization(self):
        """
        Verifies presence of standard organizational directory structures.
        """
        root_items = set(os.listdir(self.base_path))
        
        good_patterns = {'src', 'lib', 'modules', 'packages', 'tests', 'docs', 'config'}
        has_good_structure = len(root_items & good_patterns) > 0
        
        if not has_good_structure:
            self.quality_score -= 5
            self.issues.append("No clear module organization detected")

    def _check_duplication(self):
        """
        Identifies duplicate source code files while excluding initialization files.
        """
        file_hashes = {}
        duplicates = 0
        
        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for file in files:
                if file.endswith('.py') and file != '__init__.py':
                    full_path = os.path.join(root, file)
                    try:
                        with open(full_path, 'rb') as f:
                            content_hash = hash(f.read())
                        
                        if content_hash in file_hashes:
                            duplicates += 1
                        else:
                            file_hashes[content_hash] = full_path
                    except Exception as e:
                        logger.debug(f"Could not read file {full_path} for duplication check: {e}")
    
        if duplicates > 0:
            self.quality_score -= (5 * min(duplicates, 3))
            self.issues.append(f"Found {duplicates} duplicate files")

    def _check_missing_init_files(self):
        """
        Detects missing __init__.py files in Python package directories.
        """
        missing_init_count = 0
        
        for root, dirs, files in os.walk(self.base_path):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            python_files = [f for f in files if f.endswith('.py')]
            if python_files and '__init__.py' not in files:
                if root != self.base_path and not root.endswith(('tests', 'docs', 'scripts')):
                    missing_init_count += 1
        
        if missing_init_count > 0:
            self.quality_score -= (5 * min(missing_init_count, 3))
            self.issues.append(f"Missing __init__.py files in {missing_init_count} directories")

    def is_structure_good(self, threshold: float = 100.0) -> bool:
        """
        Determines if repository structure meets quality threshold.

        Args:
            threshold: Minimum quality score required for "good" classification.

        Returns:
            bool: True if quality score meets or exceeds threshold.
        """
        return self.quality_score >= threshold


class RepoOrganizer:
    """
    Analyzes and reorganizes repository structure using AI models.

    Combines automated analysis with AI-powered reorganization planning
    to improve repository maintainability and adherence to best practices.
    """

    def __init__(self, config_loader: ConfigLoader, prompts: PromptLoader):
        """
        Initializes the repository organizer with configuration and prompts.

        Args:
            config_loader: Configuration loader with repository and model settings.
            prompts: Prompt loader for AI model interaction templates.
        """
        self.config = config_loader.config
        self.prompts = prompts
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.repo_name = parse_folder_name(self.repo_url)
        
        self.import_analyzer = ImportAnalyzer(self.base_path)
        self.quality_validator = StructureQualityValidator(self.base_path)

    def get_repo_structure(self) -> str:
        """
        Generates a tree representation of repository structure.

        Returns:
            str: Formatted tree structure as a string.
        """
        tree_structure = []
        base_path_obj = Path(self.base_path)

        def build_tree(path: Path, prefix: str = "", is_last: bool = True):
            items = [item for item in sorted(path.iterdir()) if not item.name.startswith('.')]
            files = [item for item in items if item.is_file()]
            dirs = [item for item in items if item.is_dir()]

            connector = "└── " if is_last else "├── "

            if path == base_path_obj:
                dir_name = self.repo_name
                tree_structure.append(f"{connector} {dir_name}/")
            else:
                tree_structure.append(f"{prefix}{connector} {path.name}/")

            new_prefix = prefix + (" " if is_last else "│ ")

            for i, file_path in enumerate(files):
                file_is_last = (i == len(files) - 1) and (not dirs)
                file_connector = "└── " if file_is_last else "├── "
                tree_structure.append(f"{new_prefix}{file_connector} {file_path.name}")

            for i, directory in enumerate(dirs):
                dir_is_last = (i == len(dirs) - 1)
                build_tree(directory, new_prefix, dir_is_last)

        build_tree(base_path_obj, "", True)
        return "\n".join(tree_structure)

    def _extract_json_from_response(self, response: str) -> Dict[str, Any]:
        """
        Extracts JSON data from AI model response.

        Handles various response formats including markdown code blocks.

        Args:
            response: Raw response string from AI model.

        Returns:
            Dict[str, Any]: Parsed JSON data as dictionary.

        Raises:
            json.JSONDecodeError: If no valid JSON can be extracted from response.
        """
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            pass

        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'```javascript\s*(.*?)\s*```',
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                try:
                    return json.loads(matches[0])
                except json.JSONDecodeError:
                    continue

        try:
            start = response.find('{')
            end = response.rfind('}') + 1
            if start != -1 and end != 0:
                json_str = response[start:end]
                return json.loads(json_str)
        except (json.JSONDecodeError, ValueError):
            pass

        raise json.JSONDecodeError("Could not extract valid JSON from response", response, 0)

    def validate_structure_quality(self) -> Tuple[float, List[str], bool]:
        """
        Evaluates current repository structure quality.

        Returns:
            Tuple[float, List[str], bool]: Quality score, list of issues, and whether structure is good.
        """
        logger.info("Validating repository structure quality...")
        quality_score, issues = self.quality_validator.validate_structure()
        is_good = self.quality_validator.is_structure_good()
        
        logger.info(f"Structure quality score: {quality_score:.1f}/100")
        if issues:
            for issue in issues:
                logger.info(f"  - {issue}")
        
        if is_good:
            logger.info("Structure is already well-organized. No changes recommended.")
        
        return quality_score, issues, is_good

    def generate_reorganization_plan(self) -> Dict[str, Any]:
        """
        Generates repository reorganization plan using AI model.

        Returns:
            Dict[str, Any]: JSON plan containing list of actions to execute.

        Raises:
            json.JSONDecodeError: If AI response cannot be parsed as valid JSON.
        """
        tree_structure = self.get_repo_structure()
        prompt = PromptBuilder.render(
            self.prompts.get("repo_organization.main_prompt"),
            tree_structure=tree_structure,
        )

        try:
            response = self.model_handler.send_request(prompt)
            logger.debug(f"Model response: {response}")

            plan = self._extract_json_from_response(response)

            return plan

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from model response: {e}")
            logger.error(f"Raw response: {response}")
            raise
        except Exception as e:
            logger.error(f"Error generating reorganization plan: {e}")
            raise

    def _update_imports_for_moved_file(self, old_path: str, new_path: str):
        """
        Updates import statements in all files referencing a moved module.

        Args:
            old_path: Original path of the moved module.
            new_path: New path after relocation.
        """
        old_module = old_path.replace('.py', '').replace('/', '.')
        new_module = new_path.replace('.py', '').replace('/', '.')
        
        importing_files = self.import_analyzer.get_files_importing_module(old_path)
        
        for file_path in importing_files:
            updated_content = self.import_analyzer.update_imports_in_file(
                file_path, old_module, new_module
            )
            
            if updated_content:
                actual_path = self.import_analyzer._resolve_current_path(file_path)
                full_path = os.path.join(self.base_path, actual_path)
                try:
                    with open(full_path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    logger.info(f"Updated imports in {file_path}")
                except Exception as e:
                    logger.error(f"Failed to update imports in {file_path}: {e}")

    def _validate_plan(self, plan: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates reorganization plan for safety and correctness.

        Args:
            plan: Dictionary containing reorganization actions.

        Returns:
            Tuple[bool, List[str]]: Validation success status and list of issues found.
        """
        actions = plan.get("actions", [])
        issues = []
        
        for action in actions:
            action_type = action.get("type")
            
            if action_type == "create_file":
                path = action.get("path")
                full_path = os.path.join(self.base_path, path)
                if os.path.exists(full_path):
                    issues.append(f"File already exists: {path}")
                    
            elif action_type == "create_directory":
                path = action.get("path")
                full_path = os.path.join(self.base_path, path)
                if os.path.exists(full_path):
                    issues.append(f"Directory already exists: {path}")
                    
            elif action_type == "rename_file":
                old_path = action.get("old_path")
                new_path = action.get("new_path")
                old_full = os.path.join(self.base_path, old_path)
                new_full = os.path.join(self.base_path, new_path)
                
                if not os.path.exists(old_full):
                    issues.append(f"Source file does not exist: {old_path}")
                if os.path.exists(new_full):
                    issues.append(f"Destination file already exists: {new_path}")
                if old_path == new_path:
                    issues.append(f"Rename source and destination are the same: {old_path}")
                    
            elif action_type == "move_file":
                source = action.get("source")
                destination = action.get("destination")
                source_full = os.path.join(self.base_path, source)
                dest_full = os.path.join(self.base_path, destination)
                
                if not os.path.exists(source_full):
                    issues.append(f"Source file does not exist: {source}")
                if os.path.exists(dest_full):
                    issues.append(f"Destination file already exists: {destination}")
                    
            elif action_type == "delete_file":
                path = action.get("path")
                full_path = os.path.join(self.base_path, path)
                if not os.path.exists(full_path):
                    issues.append(f"File to delete does not exist: {path}")
                    
            elif action_type == "delete_directory":
                path = action.get("path")
                full_path = os.path.join(self.base_path, path)
                if not os.path.exists(full_path):
                    issues.append(f"Directory to delete does not exist: {path}")
                elif os.listdir(full_path):
                    issues.append(f"Directory is not empty: {path}")
        
        filtered_actions = self._filter_redundant_actions(actions)
        
        if len(filtered_actions) != len(actions):
            logger.warning(f"Filtered out {len(actions) - len(filtered_actions)} redundant actions")
            plan["actions"] = filtered_actions
            
        return len(issues) == 0, issues

    def _filter_redundant_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Removes redundant or unnecessary actions from reorganization plan.

        Args:
            actions: List of action dictionaries to filter.

        Returns:
            List[Dict[str, Any]]: Filtered list of actions.
        """
        filtered_actions = []
        existing_files = set()
        
        for action in actions:
            if action["type"] in ["rename_file", "move_file"]:
                old_path = action.get("old_path")
                if old_path:
                    existing_files.add(old_path)
        
        for action in actions:
            action_type = action["type"]
            should_include = True
            
            if action_type == "create_file":
                path = action.get("path")
                full_path = os.path.join(self.base_path, path)
                if os.path.exists(full_path):
                    if os.path.getsize(full_path) > 0:
                        should_include = False
                        
            elif action_type == "rename_file":
                old_path = action.get("old_path")
                new_path = action.get("new_path")
                if old_path == new_path:
                    should_include = False
                    
            elif action_type == "create_directory":
                path = action.get("path")
                full_path = os.path.join(self.base_path, path)
                if os.path.exists(full_path):
                    should_include = False
            
            if should_include:
                filtered_actions.append(action)
        
        return filtered_actions

    def _reorder_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Reorders actions to ensure proper execution sequence.

        Args:
            actions: List of action dictionaries.

        Returns:
            List[Dict[str, Any]]: Reordered list of actions.
        """
        priority_map = {
            'create_directory': 1,
            'move_file': 2,
            'rename_file': 3,
            'delete_file': 4,
            'create_file': 5,
            'delete_directory': 6,
        }
        
        return sorted(actions, key=lambda a: priority_map.get(a['type'], 99))

    def execute_reorganization(self, plan: Dict[str, Any]):
        """
        Executes validated reorganization plan.

        Args:
            plan: Dictionary containing validated reorganization actions.
        """
        is_valid, issues = self._validate_plan(plan)
        
        if not is_valid:
            if issues:
                logger.warning("Skipping reorganization due to validation issues")
            return
        
        actions = plan.get("actions", [])
        
        if not actions:
            return
        
        actions = self._reorder_actions(actions)
        
        processed_files = set()
        moved_file_map = {}

        for action in actions:
            try:
                action_type = action["type"]
                
                if action_type == "create_directory":
                    self._create_directory(action["path"])
                    
                elif action_type == "move_file":
                    self._move_file(action["source"], action["destination"])
                    moved_file_map[action["source"]] = action["destination"]
                    self.import_analyzer.moved_files[action["source"]] = action["destination"]
                    self._update_imports_for_moved_file(action["source"], action["destination"])
                    processed_files.add(action["source"])
                    
                elif action_type == "delete_file":
                    if action["path"] not in processed_files:
                        self._delete_file(action["path"])
                        
                elif action_type == "delete_directory":
                    self._delete_directory(action["path"])
                    
                elif action_type == "create_file":
                    self._create_file(action["path"], action.get("content", ""))
                    
                elif action_type == "rename_file":
                    self._rename_file(action["old_path"], action["new_path"])
                    moved_file_map[action["old_path"]] = action["new_path"]
                    self.import_analyzer.moved_files[action["old_path"]] = action["new_path"]
                    self._update_imports_for_moved_file(action["old_path"], action["new_path"])
                    
                else:
                    logger.warning(f"Unknown action type: {action_type}")
            except Exception as e:
                logger.error(f"Error executing action {action}: {e}")

    def _create_directory(self, path: str):
        """
        Creates directory at specified path if it doesn't exist.

        Args:
            path: Relative path for directory creation.
        """
        full_path = os.path.join(self.base_path, path)
        if not os.path.exists(full_path):
            os.makedirs(full_path, exist_ok=True)
            logger.info(f"Created directory: {path}")

    def _move_file(self, source: str, destination: str):
        """
        Moves file from source to destination path.

        Args:
            source: Current relative path of the file.
            destination: New relative path for the file.
        """
        source_path = os.path.join(self.base_path, source)
        dest_path = os.path.join(self.base_path, destination)

        if not os.path.exists(source_path):
            return
        
        if os.path.exists(dest_path):
            return

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)

        os.rename(source_path, dest_path)
        logger.info(f"Moved file: {source} -> {destination}")

    def _delete_file(self, path: str):
        """
        Deletes file at specified path.

        Args:
            path: Relative path of file to delete.
        """
        full_path = os.path.join(self.base_path, path)
        if os.path.exists(full_path):
            os.remove(full_path)
            logger.info(f"Deleted file: {path}")

    def _delete_directory(self, path: str):
        """
        Deletes empty directory at specified path.

        Args:
            path: Relative path of directory to delete.
        """
        full_path = os.path.join(self.base_path, path)
        if os.path.exists(full_path) and os.path.isdir(full_path):
            if not os.listdir(full_path):
                os.rmdir(full_path)
                logger.info(f"Deleted empty directory: {path}")

    def _create_file(self, path: str, content: str = ""):
        """
        Creates new file with specified content.

        Args:
            path: Relative path for new file.
            content: Content to write to the file.
        """
        full_path = os.path.join(self.base_path, path)
        
        if os.path.exists(full_path):
            return

        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(content)
        logger.info(f"Created file: {path}")

    def _rename_file(self, old_path: str, new_path: str):
        """
        Renames file while preserving content.

        Args:
            old_path: Current relative path of the file.
            new_path: New relative path for the file.
        """
        old_full_path = os.path.join(self.base_path, old_path)
        new_full_path = os.path.join(self.base_path, new_path)

        if not os.path.exists(old_full_path):
            return
        
        if os.path.exists(new_full_path):
            return

        try:
            with open(old_full_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            content = ""

        os.makedirs(os.path.dirname(new_full_path), exist_ok=True)

        os.rename(old_full_path, new_full_path)
        logger.info(f"Renamed file: {old_path} -> {new_path}")

        if content and os.path.exists(new_full_path):
            old_ext = os.path.splitext(old_path)[1]
            new_ext = os.path.splitext(new_path)[1]
            if old_ext != new_ext:
                with open(new_full_path, 'w', encoding='utf-8') as f:
                    f.write(content)

    def reorganize(self):
        """
        Executes complete repository reorganization workflow.

        Performs structure validation, generates AI-powered reorganization plan,
        validates the plan, and executes it if appropriate.
        """
        logger.info("Starting repository structure analysis...")
        
        quality_score, issues, is_structure_good = self.validate_structure_quality()
        
        if is_structure_good:
            logger.info("Repository structure is already well-organized. Skipping reorganization.")
            return
        
        self.import_analyzer.build_import_map()
        
        tree_structure = self.get_repo_structure()
        logger.debug(f"Repository structure:\n{tree_structure}")
        
        logger.info("Generating reorganization plan...")
        plan = self.generate_reorganization_plan()
        
        logger.info("Executing reorganization plan...")
        self.execute_reorganization(plan)
        
        logger.info("Repository reorganization completed!")