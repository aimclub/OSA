"""Main orchestrator for repository reorganization."""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.organization.core.analyzers.base import BaseAnalyzer
from osa_tool.organization.core.analyzers.factory import AnalyzerFactory
from osa_tool.organization.core.utils import extract_error_files_advanced
from osa_tool.organization.core.executor.action_executor import ActionExecutor
from osa_tool.organization.core.health_checker import HealthChecker
from osa_tool.organization.core.planning_manager import PlanningManager
from osa_tool.organization.core.snapshot_manager import SnapshotManager
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class RepoOrganizer:
    """
    Main orchestrator: detects project type, builds import maps, plans and executes reorganization.

    Coordinates all aspects of repository reorganization including:
    - Project type detection
    - Import map building
    - Plan generation and validation
    - Snapshot creation and rollback
    - Action execution
    - Health checking and error fixing
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initialize the repository organizer.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("general")
        self.prompts = self.config_manager.get_prompts()
        self.model_handler = ModelHandlerFactory.build(self.model_settings)
        self.repo_url = self.config_manager.get_git_settings().repository
        self.base_path = Path(os.getcwd()) / parse_folder_name(self.repo_url)
        self.repo_name = self.base_path.name
        self.analyzers: Dict[str, BaseAnalyzer] = {}
        self.moved_files: Dict[str, str] = {}
        self.project_type = self._detect_project_type()
        self.planning = PlanningManager(self.model_handler, self.prompts, self.base_path, self.project_type)
        self.health = HealthChecker(self.base_path, self.project_type, self.model_handler, self.prompts)
        self.snapshot = SnapshotManager(self.base_path)

    def _detect_project_type(self) -> str:
        """
        Detect the project type based on files present in the repository.

        Analyzes file extensions and key project files to determine the
        primary programming language of the project.

        Returns:
            str: Detected project type ('python', 'java', etc.) or 'unknown'/'mixed'
        """
        key_files = {
            "python": ["requirements.txt", "setup.py", "pyproject.toml", "__init__.py", ".py"],
            "java": ["pom.xml", "build.gradle", "build.sbt", ".java", "gradlew"],
            "javascript": ["package.json", "package-lock.json", "yarn.lock", "node_modules", ".js", ".ts"],
            "go": ["go.mod", "go.sum", "main.go", ".go"],
            "cpp": ["CMakeLists.txt", "Makefile", ".c", ".cpp", ".h", ".hpp"],
            "rust": ["Cargo.toml", "Cargo.lock", ".rs"],
            "latex": [".tex", ".bib", ".sty", ".cls"],
            "csharp": [".csproj", ".sln", ".cs"],
            "swift": ["Package.swift", ".swift"],
            "ruby": ["Gemfile", "Gemfile.lock", ".rb", ".gemspec"],
            "kotlin": ["build.gradle.kts", ".kt", ".kts"],
        }
        counts = {lang: 0 for lang in key_files}
        for root, dirs, files in os.walk(self.base_path):
            for file in files:
                for lang, indicators in key_files.items():
                    if file in indicators:
                        counts[lang] += 1
                    elif any(file.endswith(ext) for ext in indicators if ext.startswith(".")):
                        counts[lang] += 1
        counts = {k: v for k, v in counts.items() if v > 0}
        if not counts:
            return "unknown"
        max_lang = max(counts.items(), key=lambda x: x[1])
        if len(counts) > 1 and max_lang[1] / sum(counts.values()) < 0.7:
            return "mixed"
        return max_lang[0]

    def _init_analyzers(self):
        """
        Initialize all required analyzers for the project.

        Creates language-specific analyzers based on detected project type
        and adds a generic analyzer for other file types.
        """
        if self.analyzers:
            return

        if self.project_type == "mixed" or self.project_type == "unknown":
            languages = AnalyzerFactory.get_supported_languages()
        else:
            languages = [self.project_type]

        for lang in languages:
            analyzer = AnalyzerFactory.create_analyzer(lang, str(self.base_path))
            if analyzer:
                self.analyzers[lang] = analyzer
            else:
                logger.warning("No analyzer available for language: %s", lang)

        covered_extensions = set()
        for analyzer in self.analyzers.values():
            covered_extensions.update(analyzer.file_extensions)

        generic = AnalyzerFactory.create_generic_analyzer(str(self.base_path), covered_extensions)
        self.analyzers["generic"] = generic

    def _build_import_maps(self):
        """
        Build import maps for all analyzers.

        Discovers files and builds import dependency maps for each
        language-specific analyzer.
        """
        self._init_analyzers()
        for analyzer in self.analyzers.values():
            analyzer.discover_files()
            analyzer.build_import_map()

    def get_repo_structure(self) -> str:
        """
        Generate a tree representation of the repository structure.

        Returns:
            str: ASCII tree representation of the repository
        """
        lines = []

        def build_tree(path: Path, prefix: str = "", is_last: bool = True):
            """
            Recursively build tree representation.

            Args:
                path: Current path to process
                prefix: Prefix string for indentation
                is_last: Whether this is the last item in its parent
            """
            items = [item for item in sorted(path.iterdir()) if not item.name.startswith(".")]
            files = [item for item in items if item.is_file()]
            dirs = [item for item in items if item.is_dir()]

            if path != self.base_path:
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector} {path.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
            else:
                new_prefix = prefix

            for i, f in enumerate(files):
                file_last = (i == len(files) - 1) and not dirs
                file_con = "└── " if file_last else "├── "
                lines.append(f"{new_prefix}{file_con} {f.name}")

            for i, d in enumerate(dirs):
                dir_last = i == len(dirs) - 1
                build_tree(d, new_prefix, dir_last)

        build_tree(self.base_path)
        return "\n".join(lines)

    def _clean_pycache(self):
        """
        Remove __pycache__ directories and .pyc files before committing.

        Cleans up Python bytecode files that shouldn't be committed.

        Returns:
            bool: True if cleanup succeeded or partially succeeded
        """
        try:
            if sys.platform == "win32":
                for root, dirs, files in os.walk(self.base_path):
                    if "__pycache__" in dirs:
                        pycache_path = Path(root) / "__pycache__"
                        shutil.rmtree(pycache_path, ignore_errors=True)
                        logger.debug(f"Removed {pycache_path}")
                    for file in files:
                        if file.endswith(".pyc"):
                            pyc_path = Path(root) / file
                            pyc_path.unlink()
                            logger.debug(f"Removed {pyc_path}")
            else:
                subprocess.run(
                    ["find", ".", "-type", "d", "-name", "__pycache__", "-exec", "rm", "-rf", "{}", "+"],
                    cwd=self.base_path,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["find", ".", "-name", "*.pyc", "-delete"], cwd=self.base_path, check=True, capture_output=True
                )
            logger.debug("Cleaned __pycache__ directories and .pyc files")
            return True
        except Exception as e:
            logger.warning("Failed to clean pycache: %s", e)
            return False

    def organize(self):
        """
        Execute the complete reorganization process.

        Performs the following steps:
        1. Pre-reorganization health check
        2. Create snapshot
        3. Generate reorganization plan
        4. Validate plan
        5. Execute reorganization
        6. Post-reorganization health check
        7. Transfer changes back to original branch
        """
        logger.info("Starting repository reorganization for: %s", self.repo_name)
        logger.info("Project type detected: %s", self.project_type)

        logger.info("PHASE 1: Pre‑reorganization health check")
        is_healthy, errors = self.health.check_health()
        if not is_healthy:
            logger.warning("Project has issues before reorganization (see debug log for details)")

            hint = self.health._get_compiler_hint()
            error_files = extract_error_files_advanced(errors, self.base_path, hint)
            if error_files:
                logger.info("Attempting to fix %d files...", len(error_files))
                fixed = self.health.fix_errors_with_llm(errors, error_files)
                if fixed:
                    logger.info("Pre‑reorganization issues fixed.")
                else:
                    logger.error("Could not fix pre‑reorganization issues automatically.")
            else:
                logger.warning("No specific files identified for fixing.")
        else:
            logger.info("Project is healthy before reorganization.")

        logger.info("PHASE 2: Creating project snapshot")
        if not self.snapshot.create_snapshot():
            logger.error("Failed to create snapshot, aborting.")
            return

        try:
            logger.info("PHASE 3: Generating reorganization plan")
            tree = self.get_repo_structure()
            logger.info("Generating plan using AI...")

            plan = self.planning.generate_plan(tree, self.repo_name)
            actions = plan.get("actions", [])

            suggested = plan.get("suggested_names", [])
            if suggested:
                logger.info("LLM suggested alternative repository names:")
                for name in suggested:
                    logger.info(f"  - {name}")

            logger.info("PHASE 4: Validating plan programmatically")
            valid, issues = self.planning.validate_actions(actions)
            max_attempts = 3
            attempt = 0
            while not valid and attempt < max_attempts:
                attempt += 1
                logger.warning(f"Plan validation failed (attempt {attempt}):")
                for issue in issues:
                    logger.warning(f"  * {issue}")
                logger.info("Asking LLM to correct the plan...")
                corrected_plan = self.planning.validate_plan_with_ai(plan, tree, issues=issues)
                plan = corrected_plan
                actions = plan.get("actions", [])
                valid, issues = self.planning.validate_actions(actions)

            if not valid:
                logger.error("Plan validation failed after %d attempts. Rolling back...", max_attempts)
                self.snapshot.rollback()
                return

            logger.info("Plan validation passed")

            logger.info("PHASE 5: Executing reorganization")
            actions = self.planning.reorder_actions(actions)
            logger.info("Building dependency maps (including generic references)...")
            self._build_import_maps()

            executor = ActionExecutor(self.base_path, self.analyzers)
            executor.execute_all(actions)

            logger.info("Committing reorganization changes to temporary branch...")
            self._clean_pycache()

            try:
                subprocess.run(["git", "add", "-A"], cwd=self.base_path, check=True, capture_output=True)
                status = subprocess.run(
                    ["git", "status", "--porcelain"], cwd=self.base_path, capture_output=True, text=True, check=True
                )
                if status.stdout.strip():
                    subprocess.run(
                        ["git", "commit", "-m", "OSA Tool: reorganization changes"],
                        cwd=self.base_path,
                        check=True,
                        capture_output=True,
                    )
                    logger.info("Changes committed to %s", self.snapshot.temp_branch)
                else:
                    logger.info("No changes to commit in temporary branch.")
            except subprocess.CalledProcessError as e:
                logger.error("Failed to commit reorganization changes: %s", e.stderr)
                self.snapshot.rollback()
                return

            logger.info("PHASE 6: Post‑reorganization health check")
            is_healthy_post, errors_post = self.health.check_health()
            if not is_healthy_post:
                logger.warning("Project has issues after reorganization (see debug log for details)")
                hint = self.health._get_compiler_hint()
                error_files_post = extract_error_files_advanced(errors_post, self.base_path, hint)
                if error_files_post:
                    logger.info("Attempting to fix %d files...", len(error_files_post))
                    fixed_post = self.health.fix_errors_with_llm(errors_post, error_files_post)
                    if fixed_post:
                        logger.info("Post‑reorganization issues fixed.")
                        is_healthy_post, _ = self.health.check_health()
                if not is_healthy_post:
                    logger.error("Project still unhealthy after reorganization. Rolling back...")
                    if self.snapshot.rollback():
                        logger.info("Rollback successful.")
                    else:
                        logger.error("Rollback failed. Manual intervention required.")
                else:
                    logger.info("Project is healthy after reorganization.")
            else:
                logger.info("Project is healthy after reorganization.")

            logger.info("Reorganization completed successfully.")

            if not self.snapshot.transfer_changes():
                logger.error("Failed to transfer changes back to original branch.")

        except Exception as e:
            logger.error("Error during reorganization: %s", e)
            logger.exception("Detailed error trace:")
            logger.warning("Rolling back...")
            self.snapshot.rollback()
            raise
