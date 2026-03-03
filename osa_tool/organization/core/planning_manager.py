"""Planning manager for generating and validating reorganization plans using LLM."""

import os
import json
from pathlib import Path
from typing import List, Optional, Tuple, Set
from collections import defaultdict

from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor, JsonParseError
from osa_tool.core.llm.llm import ModelHandler


class PlanningManager:
    """
    Generates and validates reorganization plans using LLM.

    Handles plan generation, validation, and correction through AI assistance.
    Provides comprehensive plan analysis and dependency checking.
    """

    def __init__(self, model_handler: ModelHandler, prompts: dict, base_path: Path, project_type: str):
        """
        Initialize the planning manager.

        Args:
            model_handler: Handler for LLM interactions
            prompts: Dictionary of prompt templates
            base_path: Root directory path
            project_type: Type of project
        """
        self.model_handler = model_handler
        self.prompts = prompts
        self.base_path = base_path
        self.project_type = project_type

    def generate_plan(self, tree_structure: str, repo_name: str) -> dict:
        """
        Generate a reorganization plan using LLM.

        Args:
            tree_structure: Tree representation of repository structure
            repo_name: Name of the repository

        Returns:
            dict: Generated plan with actions and metadata
        """
        prompt_template = self.prompts.get("repo_organization.plan_prompt")
        if not prompt_template:
            raise ValueError("plan_prompt not found in configuration")
        prompt = PromptBuilder.render(
            prompt_template,
            repo_name=repo_name,
            tree_structure=tree_structure,
        )
        response = self.model_handler.send_request(prompt)
        logger.debug("LLM plan response: %s", response)
        plan = JsonProcessor.parse(response, expected_type=dict)
        if "analysis_summary" not in plan:
            plan["analysis_summary"] = {}
        if "project_type" not in plan["analysis_summary"]:
            plan["analysis_summary"]["project_type"] = self.project_type
        if "suggested_names" not in plan:
            plan["suggested_names"] = []
        return plan

    def validate_plan_with_ai(self, plan: dict, tree_structure: str, issues: Optional[List[str]] = None) -> dict:
        """
        Validate and potentially correct a plan using LLM.

        Args:
            plan: Original plan to validate
            tree_structure: Tree representation of repository structure
            issues: List of validation issues found

        Returns:
            dict: Validated or corrected plan
        """
        prompt_template = self.prompts.get("repo_organization.validation_prompt")
        if not prompt_template:
            raise ValueError("validation_prompt not found in configuration")
        prompt = PromptBuilder.render(
            prompt_template, tree_structure=tree_structure, proposed_plan=json.dumps(plan, ensure_ascii=False, indent=2)
        )
        if issues:
            prompt += "\n\nAdditional validation issues that need to be addressed:\n" + "\n".join(issues)
        response = self.model_handler.send_request(prompt)
        logger.debug("LLM validation response: %s", response)
        try:
            validation = JsonProcessor.parse(response, expected_type=dict)
            if validation.get("corrected_plan"):
                corrected = validation["corrected_plan"]
                logger.info("LLM provided corrected plan with %d actions", len(corrected.get("actions", [])))
                return corrected
        except JsonParseError as e:
            logger.error(f"Failed to parse validation response: {e}")
        except Exception as e:
            logger.error(f"Error during plan validation: {e}")

        logger.warning("Using original plan due to validation error")
        return plan

    def validate_actions(self, actions: List[dict]) -> Tuple[bool, List[str]]:
        """
        Programmatically validate a list of actions for consistency and safety.

        Checks for:
        - Missing required fields
        - File/directory existence
        - Circular dependencies
        - Conflicting operations
        - Directory creation requirements

        Args:
            actions: List of action dictionaries to validate

        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_issues)
        """
        issues = []
        sources = set()
        destinations = set()
        created_paths = set()
        for action in actions:
            if action["type"] in ("create_directory", "create_file"):
                created_paths.add(action["path"])

        for action in actions:
            if action["type"] in ("move_file", "rename_file"):
                dst = action.get("destination") or action.get("new_path")
                if dst:
                    dst_dir = str(Path(dst).parent)
                    if dst_dir and dst_dir != ".":
                        created_paths.add(dst_dir)
            elif action["type"] == "move_directory":
                dst = action.get("destination")
                if dst:
                    dst_dir = str(Path(dst).parent)
                    if dst_dir and dst_dir != ".":
                        created_paths.add(dst_dir)

        for i, action in enumerate(actions):
            typ = action["type"]

            if typ in ("move_file", "rename_file"):
                src = action.get("source") or action.get("old_path")
                dst = action.get("destination") or action.get("new_path")

                if not src or not dst:
                    issues.append(f"Action {i}: Missing source or destination")
                    continue

                src_path = self.base_path / src
                if not src_path.exists():
                    if src not in created_paths:
                        issues.append(f"Source does not exist and not created in plan: {src}")

                dst_path = self.base_path / dst
                if dst_path.exists() and dst not in created_paths:
                    issues.append(f"Destination already exists: {dst}")

                if src == dst:
                    issues.append(f"Source and destination are the same: {src}")

                sources.add(src)
                destinations.add(dst)

            elif typ == "move_directory":
                src = action.get("source")
                dst = action.get("destination")
                if not src or not dst:
                    issues.append(f"Action {i}: Missing source or destination for move_directory")
                    continue
                src_path = self.base_path / src
                if not src_path.exists():
                    if src not in created_paths:
                        issues.append(f"Source directory does not exist and not created in plan: {src}")
                dst_path = self.base_path / dst
                if dst_path.exists() and dst not in created_paths:
                    issues.append(f"Destination directory already exists: {dst}")
                if src == dst:
                    issues.append(f"Source and destination are the same: {src}")
                sources.add(src)
                destinations.add(dst)

            elif typ == "move_files":
                pattern = action.get("source_pattern")
                dest_dir = action.get("destination_dir")
                if not pattern or not dest_dir:
                    issues.append(f"Action {i}: Missing source_pattern or destination_dir")
                    continue
                if ".." in pattern or pattern.startswith("/"):
                    issues.append(f"Action {i}: Invalid pattern '{pattern}' (cannot contain '..' or start with '/')")
                if os.path.isabs(dest_dir):
                    issues.append(f"Action {i}: destination_dir must be relative, got '{dest_dir}'")
                full_dest = self.base_path / dest_dir
                if not full_dest.exists() and dest_dir not in created_paths:
                    created_paths.add(dest_dir)

            elif typ == "create_file":
                dst = action["path"]
                full_path = self.base_path / dst
                if full_path.exists() and dst not in created_paths:
                    issues.append(f"File already exists: {dst}")
                destinations.add(dst)
                created_paths.add(dst)

            elif typ == "create_directory":
                dst = action["path"]
                full_path = self.base_path / dst
                if full_path.exists() and dst not in created_paths:
                    if full_path.is_file():
                        issues.append(f"Path exists as file, cannot create directory: {dst}")
                destinations.add(dst)
                created_paths.add(dst)

            elif typ == "delete_file":
                src = action["path"]
                full_path = self.base_path / src
                if not full_path.exists() and src not in created_paths:
                    issues.append(f"File to delete does not exist: {src}")
                sources.add(src)

            elif typ == "delete_directory":
                src = action["path"]
                full_path = self.base_path / src

                if not full_path.exists() and src not in created_paths:
                    issues.append(f"Directory to delete does not exist: {src}")
                sources.add(src)

            else:
                logger.warning(f"Unknown action type in validation: {typ}")

        move_pairs = []
        for action in actions:
            if action["type"] in ("move_file", "rename_file"):
                src = action.get("source") or action.get("old_path")
                dst = action.get("destination") or action.get("new_path")
                if src and dst:
                    move_pairs.append((src, dst))
            elif action["type"] == "move_directory":
                src = action.get("source")
                dst = action.get("destination")
                if src and dst:
                    move_pairs.append((src, dst))

        graph = defaultdict(list)
        for src, dst in move_pairs:
            graph[src].append(dst)

        visited = set()
        recursion_stack = set()

        def has_cycle(node: str, path: Set[str]) -> bool:
            """
            Check for cycles in move graph using DFS.

            Args:
                node: Current node to check
                path: Set of nodes in current path

            Returns:
                bool: True if cycle detected, False otherwise
            """
            if node in path:
                return True
            if node in visited:
                return False
            path.add(node)
            for neighbor in graph.get(node, []):
                if has_cycle(neighbor, path):
                    return True
            path.remove(node)
            visited.add(node)
            return False

        for src in graph:
            if has_cycle(src, set()):
                issues.append(f"Move cycle detected involving {src}")
                break

        for action in actions:
            if action["type"] in ("move_file", "rename_file"):
                dst = action.get("destination") or action.get("new_path")
                if dst:
                    dst_dir = str(Path(dst).parent)
                    if dst_dir and dst_dir != ".":
                        dir_exists = (self.base_path / dst_dir).exists()
                        dir_created = dst_dir in created_paths
                        if not dir_exists and not dir_created:
                            issues.append(
                                f"Destination directory does not exist and not scheduled for creation: {dst_dir}"
                            )
            elif action["type"] == "move_directory":
                dst = action.get("destination")
                if dst:
                    dst_dir = str(Path(dst).parent)
                    if dst_dir and dst_dir != ".":
                        dir_exists = (self.base_path / dst_dir).exists()
                        dir_created = dst_dir in created_paths
                        if not dir_exists and not dir_created:
                            issues.append(
                                f"Destination directory does not exist and not scheduled for creation: {dst_dir}"
                            )

        path_actions = defaultdict(list)
        for i, action in enumerate(actions):
            if "path" in action:
                path_actions[action["path"]].append((i, action["type"]))
            elif "destination" in action:
                path_actions[action["destination"]].append((i, action["type"]))

        for path, acts in path_actions.items():
            if len(acts) > 1:
                types = [t for _, t in acts]
                if "delete_file" in types and "create_file" in types:
                    issues.append(f"Conflicting actions for path {path}: both delete and create")
                if "delete_directory" in types and "create_directory" in types:
                    issues.append(f"Conflicting actions for path {path}: both delete and create")

        return len(issues) == 0, issues

    @staticmethod
    def reorder_actions(actions: List[dict]) -> List[dict]:
        """
        Reorder actions to ensure safe execution order.

        Priority order:
        1. Create directories (shallow first)
        2. Move directories
        3. Move files
        4. Rename files
        5. Create files
        6. Delete files
        7. Delete directories

        Args:
            actions: List of action dictionaries

        Returns:
            List[dict]: Reordered actions
        """
        priority = {
            "create_directory": 1,
            "move_directory": 2,
            "move_files": 3,
            "move_file": 4,
            "rename_file": 4,
            "create_file": 5,
            "delete_file": 6,
            "delete_directory": 7,
        }

        sorted_actions = sorted(actions, key=lambda a: priority.get(a["type"], 99))

        dir_actions = [a for a in sorted_actions if a["type"] == "create_directory"]
        other_actions = [a for a in sorted_actions if a["type"] != "create_directory"]

        dir_actions.sort(key=lambda a: len(Path(a["path"]).parts))

        return dir_actions + other_actions

    def explain_plan(self, actions: List[dict]) -> str:
        """
        Generate a human-readable explanation of the planned actions.

        Args:
            actions: List of action dictionaries

        Returns:
            str: Human-readable explanation
        """
        if not actions:
            return "No actions planned."

        explanation = []
        explanation.append(f"Planned reorganization with {len(actions)} actions:")

        creates = [a for a in actions if a["type"] == "create_directory"]
        moves = [a for a in actions if a["type"] in ("move_file", "rename_file", "move_files", "move_directory")]
        new_files = [a for a in actions if a["type"] == "create_file"]
        deletes = [a for a in actions if a["type"] in ("delete_file", "delete_directory")]

        if creates:
            explanation.append(f"\nCreate directories ({len(creates)}):")
            for a in creates[:5]:
                explanation.append(f"  - {a['path']}")
            if len(creates) > 5:
                explanation.append(f"  ... and {len(creates) - 5} more")

        if moves:
            explanation.append(f"\nMove/rename items ({len(moves)}):")
            for a in moves[:5]:
                if a["type"] == "move_files":
                    explanation.append(f"  - {a['source_pattern']} -> {a['destination_dir']}/")
                elif a["type"] == "move_directory":
                    explanation.append(f"  - directory {a['source']} -> {a['destination']}")
                else:
                    src = a.get("source") or a.get("old_path")
                    dst = a.get("destination") or a.get("new_path")
                    explanation.append(f"  - {src} -> {dst}")
            if len(moves) > 5:
                explanation.append(f"  ... and {len(moves) - 5} more")

        if new_files:
            explanation.append(f"\nCreate files ({len(new_files)}):")
            for a in new_files[:5]:
                explanation.append(f"  - {a['path']}")
            if len(new_files) > 5:
                explanation.append(f"  ... and {len(new_files) - 5} more")

        if deletes:
            explanation.append(f"\nDelete ({len(deletes)}):")
            for a in deletes[:5]:
                explanation.append(f"  - {a['path']}")
            if len(deletes) > 5:
                explanation.append(f"  ... and {len(deletes) - 5} more")

        return "\n".join(explanation)
