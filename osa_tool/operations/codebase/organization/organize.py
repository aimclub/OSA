"""Main orchestrator for repository reorganization."""

import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, Optional

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name

from .core.analyzers.base import BaseAnalyzer
from .core.analyzers.factory import AnalyzerFactory
from .core.executor.action_executor import ActionExecutionError, ActionExecutor
from .core.health_checker import HealthChecker
from .core.planning_manager import PlanningManager
from .core.snapshot_manager import SnapshotManager
from .core.utils import extract_error_files_advanced


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

    BUILD_ARTIFACT_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox", "build", "dist"}
    BUILD_ARTIFACT_SUFFIXES = {".pyc", ".pyo", ".pyd", ".class", ".o", ".obj"}
    DOMINANT_LANGUAGE_SHARE = 0.7
    MIN_PLATFORM_LANGUAGE_SHARE = 0.1
    LANGUAGE_ALIASES = {
        "c": "cpp",
        "c#": "csharp",
        "c++": "cpp",
        "c/c++": "cpp",
        "cpp": "cpp",
        "csharp": "csharp",
        "go": "go",
        "golang": "go",
        "java": "java",
        "javascript": "javascript",
        "kotlin": "kotlin",
        "latex": "latex",
        "python": "python",
        "react jsx": "javascript",
        "react tsx": "javascript",
        "ruby": "ruby",
        "rust": "rust",
        "swift": "swift",
        "typescript": "javascript",
    }
    FILE_LANGUAGE_MAP = {
        ".py": "python",
        ".pyi": "python",
        ".java": "java",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "javascript",
        ".tsx": "javascript",
        ".go": "go",
        ".ino": "cpp",
        ".c": "cpp",
        ".cc": "cpp",
        ".cpp": "cpp",
        ".cxx": "cpp",
        ".h": "cpp",
        ".hh": "cpp",
        ".hpp": "cpp",
        ".hxx": "cpp",
        ".rs": "rust",
        ".tex": "latex",
        ".bib": "latex",
        ".sty": "latex",
        ".cls": "latex",
        ".cs": "csharp",
        ".swift": "swift",
        ".rb": "ruby",
        ".kt": "kotlin",
        ".kts": "kotlin",
    }
    BUILD_FILE_BONUSES = {
        "requirements.txt": "python",
        "setup.py": "python",
        "pyproject.toml": "python",
        "pom.xml": "java",
        "build.gradle": "java",
        "build.gradle.kts": "kotlin",
        "gradlew": "java",
        "package.json": "javascript",
        "package-lock.json": "javascript",
        "yarn.lock": "javascript",
        "go.mod": "go",
        "go.sum": "go",
        "cargo.toml": "rust",
        "cargo.lock": "rust",
        "cmakelists.txt": "cpp",
        "makefile": "cpp",
        ".csproj": "csharp",
        ".sln": "csharp",
        "package.swift": "swift",
        "gemfile": "ruby",
        "gemfile.lock": "ruby",
    }

    def __init__(self, config_manager: ConfigManager, metadata: Optional[RepositoryMetadata] = None):
        """
        Initialize the repository organizer.

        Args:
            config_manager: Configuration manager instance
            metadata: Optional repository metadata from the hosting platform
        """
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("general")
        self.prompts = self.config_manager.get_prompts()
        self.model_handler = ModelHandlerFactory.build(self.model_settings)
        self.repo_url = self.config_manager.get_git_settings().repository
        self.base_path = Path(os.getcwd()) / parse_folder_name(self.repo_url)
        self.repo_name = self.base_path.name
        self.metadata = metadata
        self.skip_health_check = bool(getattr(self.config_manager.args, "skip_health_check", False))
        self.analyzers: Dict[str, BaseAnalyzer] = {}
        self.moved_files: Dict[str, str] = {}
        self.project_type = self._detect_project_type()
        self.planning = PlanningManager(self.model_handler, self.prompts, self.base_path, self.project_type)
        self.health = HealthChecker(self.base_path, self.project_type, self.model_handler, self.prompts)
        self.snapshot = SnapshotManager(self.base_path)

    @classmethod
    def _normalize_language_name(cls, language: Optional[str]) -> Optional[str]:
        if not language:
            return None
        return cls.LANGUAGE_ALIASES.get(language.strip().lower())

    def _collect_local_language_scores(self) -> Counter:
        scores: Counter = Counter()
        for root, _, files in os.walk(self.base_path):
            for file_name in files:
                path = Path(root) / file_name
                if not path.is_file():
                    continue

                normalized_name = file_name.lower()
                build_language = self.BUILD_FILE_BONUSES.get(normalized_name)
                if build_language:
                    scores[build_language] += 50

                language = self.FILE_LANGUAGE_MAP.get(path.suffix.lower())
                if not language and not path.suffix:
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as file_obj:
                            first_line = file_obj.readline(200)
                        if first_line.startswith("#!") and "python" in first_line.lower():
                            language = "python"
                    except OSError:
                        pass
                if language:
                    # Weighting by size is more stable for mixed repos than file counts.
                    scores[language] += max(path.stat().st_size, 1)
        return scores

    def _collect_metadata_language_scores(self) -> Counter:
        scores: Counter = Counter()
        if not self.metadata:
            return scores

        language_stats = getattr(self.metadata, "language_stats", {}) or {}
        for language, weight in language_stats.items():
            normalized = self._normalize_language_name(language)
            if normalized:
                scores[normalized] += float(weight)
        if scores:
            return scores

        primary = self._normalize_language_name(self.metadata.language)
        if primary:
            scores[primary] += 5000

        for rank, language in enumerate(self.metadata.languages or []):
            normalized = self._normalize_language_name(language)
            if normalized:
                scores[normalized] += max(3000 - rank * 500, 500)
        return scores

    @classmethod
    def _filter_platform_language_scores(cls, scores: Counter) -> Counter:
        total_score = sum(scores.values())
        if total_score <= 0:
            return Counter()

        filtered = Counter(
            {
                language: score
                for language, score in scores.items()
                if (score / total_score) >= cls.MIN_PLATFORM_LANGUAGE_SHARE
            }
        )
        return filtered or Counter(scores)

    def _detect_project_type(self) -> str:
        """
        Detect the project type based on repository metadata and local files.

        Returns:
            str: Detected project type ('python', 'java', etc.) or 'unknown'/'mixed'
        """
        platform_stats = getattr(self.metadata, "language_stats", {}) if self.metadata else {}
        if platform_stats:
            scores = self._filter_platform_language_scores(self._collect_metadata_language_scores())
        else:
            metadata_scores = self._collect_metadata_language_scores()
            scores = metadata_scores if metadata_scores else self._collect_local_language_scores()
        scores = Counter({language: score for language, score in scores.items() if score > 0})

        if not scores:
            return "unknown"

        top_language, top_score = scores.most_common(1)[0]
        total_score = sum(scores.values())
        if len(scores) > 1 and total_score and (top_score / total_score) < self.DOMINANT_LANGUAGE_SHARE:
            return "mixed"
        return top_language

    def _init_analyzers(self):
        """
        Initialize all required analyzers for the project.

        Creates language-specific analyzers based on detected project type
        and adds a generic analyzer for other file types.
        """
        if self.analyzers:
            return

        if self.project_type in {"mixed", "unknown"}:
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

        def is_build_artifact(item: Path) -> bool:
            if item.name in self.BUILD_ARTIFACT_DIRS:
                return True
            return item.is_file() and item.suffix.lower() in self.BUILD_ARTIFACT_SUFFIXES

        def build_tree(path: Path, prefix: str = "", is_last: bool = True):
            items = [
                item for item in sorted(path.iterdir()) if not item.name.startswith(".") and not is_build_artifact(item)
            ]
            files = [item for item in items if item.is_file()]
            dirs = [item for item in items if item.is_dir()]

            if path != self.base_path:
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{path.name}/")
                new_prefix = prefix + ("    " if is_last else "│   ")
            else:
                new_prefix = prefix

            for i, file_path in enumerate(files):
                file_last = (i == len(files) - 1) and not dirs
                file_connector = "└── " if file_last else "├── "
                lines.append(f"{new_prefix}{file_connector}{file_path.name}")

            for i, directory in enumerate(dirs):
                dir_last = i == len(dirs) - 1
                build_tree(directory, new_prefix, dir_last)

        build_tree(self.base_path)
        return "\n".join(lines)

    def _clean_pycache(self):
        """
        Remove Python/cache build artifacts before planning and committing.

        Returns:
            bool: True if cleanup succeeded or partially succeeded
        """
        try:
            for root, dirs, files in os.walk(self.base_path):
                for cache_dir in list(dirs):
                    if cache_dir not in self.BUILD_ARTIFACT_DIRS:
                        continue
                    cache_path = Path(root) / cache_dir
                    if self._should_delete_artifact(cache_path):
                        shutil.rmtree(cache_path, ignore_errors=True)
                        dirs.remove(cache_dir)
                        logger.debug("Removed %s", cache_path)
                for file_name in files:
                    artifact_path = Path(root) / file_name
                    if artifact_path.suffix.lower() in self.BUILD_ARTIFACT_SUFFIXES and self._should_delete_artifact(
                        artifact_path
                    ):
                        artifact_path.unlink()
                        logger.debug("Removed %s", artifact_path)
            logger.debug("Cleaned cache and build artifacts")
            return True
        except Exception as exc:
            logger.warning("Failed to clean build artifacts: %s", exc)
            return False

    def _should_delete_artifact(self, path: Path) -> bool:
        rel_path = str(path.relative_to(self.base_path)).replace("\\", "/")
        if path.name in {"build", "dist"} and self._is_git_tracked(rel_path):
            logger.debug("Skipping tracked artifact directory: %s", rel_path)
            return False
        if path.is_file() and self._is_git_tracked(rel_path):
            logger.debug("Skipping tracked artifact file: %s", rel_path)
            return False
        return True

    def _is_git_tracked(self, rel_path: str) -> bool:
        try:
            result = subprocess.run(
                ["git", "ls-files", "--", rel_path],
                cwd=self.base_path,
                capture_output=True,
                text=True,
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def _run_health_phase(self, phase_label: str) -> bool:
        if self.skip_health_check:
            logger.info("%s skipped by configuration", phase_label)
            return True

        logger.info(phase_label)
        is_healthy, errors = self.health.check_health()
        if is_healthy:
            return True

        logger.warning("Project has issues during health check (see debug log for details)")
        hint = self.health._get_compiler_hint()
        error_files = extract_error_files_advanced(errors, self.base_path, hint)
        if not error_files:
            logger.warning("No specific files identified for fixing.")
            return False

        logger.info("Attempting to fix %d files...", len(error_files))
        fixed = self.health.fix_errors_with_llm(errors, error_files)
        if not fixed:
            logger.error("Could not fix health check issues automatically.")
            return False

        logger.info("Health check issues were fixed.")
        is_healthy_after_fix, _ = self.health.check_health()
        return is_healthy_after_fix

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

        pre_health_ok = self._run_health_phase("PHASE 1: Pre-reorganization health check")
        if not pre_health_ok and not self.skip_health_check:
            logger.warning("Continuing reorganization despite pre-existing health issues.")
        elif pre_health_ok and not self.skip_health_check:
            logger.info("Project is healthy before reorganization.")

        logger.info("PHASE 2: Creating project snapshot")
        if not self.snapshot.create_snapshot():
            logger.error("Failed to create snapshot, aborting.")
            return

        try:
            logger.info("PHASE 3: Generating reorganization plan")
            logger.info("Cleaning build artifacts before planning...")
            self._clean_pycache()
            tree = self.get_repo_structure()
            logger.info("Generating plan using AI...")

            plan = self.planning.generate_plan(tree, self.repo_name)
            actions = plan.get("actions", [])

            suggested = plan.get("suggested_names", [])
            if suggested:
                logger.info("LLM suggested alternative repository names:")
                for name in suggested:
                    logger.info("  - %s", name)

            logger.info("PHASE 4: Validating plan programmatically")
            valid, issues = self.planning.validate_actions(actions)
            max_attempts = 3
            attempt = 0
            while not valid and attempt < max_attempts:
                attempt += 1
                logger.warning("Plan validation failed (attempt %d):", attempt)
                for issue in issues:
                    logger.warning("  * %s", issue)
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
            if not self._commit_temp_branch_changes("OSA Tool: reorganization changes"):
                self.snapshot.rollback()
                return

            post_health_ok = self._run_health_phase("PHASE 6: Post-reorganization health check")
            if not post_health_ok and not self.skip_health_check:
                logger.error("Project still unhealthy after reorganization. Rolling back...")
                if self.snapshot.rollback():
                    logger.info("Rollback successful.")
                else:
                    logger.error("Rollback failed. Manual intervention required.")
                return
            if not self.skip_health_check:
                logger.info("Project is healthy after reorganization.")

            if not self._commit_temp_branch_changes("OSA Tool: post-health fixes"):
                self.snapshot.rollback()
                return

            if not self.snapshot.transfer_changes():
                logger.error("Failed to transfer changes back to original branch.")
                return

            logger.info("Reorganization completed successfully.")

        except ActionExecutionError as exc:
            logger.error("Reorganization action execution failed: %s", exc)
            logger.warning("Rolling back...")
            self.snapshot.rollback()
            raise

        except Exception as exc:
            logger.error("Error during reorganization: %s", exc)
            logger.exception("Detailed error trace:")
            logger.warning("Rolling back...")
            self.snapshot.rollback()
            raise

    def _commit_temp_branch_changes(self, message: str) -> bool:
        try:
            subprocess.run(["git", "add", "-A"], cwd=self.base_path, check=True, capture_output=True)
            status = subprocess.run(
                ["git", "status", "--porcelain"], cwd=self.base_path, capture_output=True, text=True, check=True
            )
            if not status.stdout.strip():
                logger.info("No changes to commit in temporary branch.")
                return True

            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.base_path,
                check=True,
                capture_output=True,
            )
            logger.info("Changes committed to %s", self.snapshot.temp_branch)
            return True
        except subprocess.CalledProcessError as exc:
            logger.error("Failed to commit temporary branch changes: %s", exc.stderr)
            return False
