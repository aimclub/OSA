import os
from abc import ABC, abstractmethod

import yaml

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigManager
from osa_tool.scheduler.todo_list import ToDoList
from osa_tool.utils.arguments_parser import get_keys_from_group_in_yaml
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name
from osa_tool.workflow.workflow_generator import GitHubWorkflowGenerator, GitLabWorkflowGenerator


class WorkflowManager(ABC):
    """
    Abstract manager for CI/CD configurations handling different platforms (GitHub, GitLab, Gitverse).

    Args:
        repo_url: Repository URL.
        metadata: Metadata object of the repository.
        args: Parsed arguments object containing CI/CD related settings.

    Raises:
        NotImplementedError: If abstract methods are not implemented in subclasses.
    """

    job_name_for_key = {
        "include_black": ["black", "lint", "Lint", "format"],
        "include_tests": ["test", "unit_tests"],
        "include_pep8": ["lint", "Lint", "pep8_check"],
        "include_autopep8": ["autopep8"],
        "include_fix_pep8": ["fix_pep8_command", "fix-pep8"],
        "slash-command-dispatch": ["slash_command_dispatch", "slashCommandDispatch"],
        "pypi-publish": ["pypi_publish", "pypi-publish"],
    }

    def __init__(self, repo_url: str, metadata: RepositoryMetadata, args, todo_list: ToDoList | None = None):
        self.repo_url = repo_url
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(repo_url))
        self.metadata = metadata
        self.workflow_keys = get_keys_from_group_in_yaml("workflow")
        self.workflow_plan = {key: value for key, value in vars(args).items() if key in self.workflow_keys}
        self.workflow_path = self._locate_workflow_path()
        self.existing_jobs = self._find_existing_jobs()
        self.todo_list = todo_list

    @abstractmethod
    def _locate_workflow_path(self) -> str | None:
        """
        Locate the path where CI/CD configuration files are stored in the repository.

        Returns:
            The path to CI/CD directory or file if exists, else None.
        """
        pass

    @abstractmethod
    def _find_existing_jobs(self) -> set[str]:
        """
        Get the set of existing job names defined in CI/CD configurations.

        Returns:
            Set of job names.
        """
        pass

    def has_python_code(self) -> bool:
        """
        Checks whether the repository contains Python code.

        Returns:
            True if Python code is present, False otherwise.
        """
        if not self.metadata.language:
            return False
        return "Python" in self.metadata.language

    def build_actual_plan(self, sourcerank: SourceRank) -> dict:
        """
        Build the workflow generation plan based on the initial plan, Python presence,
        existing jobs, and platform-specific logic.

        Args:
            sourcerank: Analyzer object to detect test presence.

        Returns:
            Dictionary representing the final workflow plan.
        """
        if not self.has_python_code():
            return {key: False for key in self.workflow_plan}

        result_plan = {}

        for key, default_value in self.workflow_plan.items():
            job_names = self.job_name_for_key.get(key)
            if job_names is None:
                result_plan[key] = default_value
                continue

            if isinstance(job_names, str):
                job_names = [job_names]

            job_exists = any(job in self.existing_jobs for job in job_names)

            if key == "include_black":
                result_plan[key] = default_value and not job_exists
            elif key == "include_tests":
                has_tests = sourcerank.tests_presence()
                result_plan[key] = default_value and has_tests and not job_exists
            elif key == "include_pep8":
                result_plan[key] = default_value and not job_exists
            elif key in ["include_autopep8", "include_fix_pep8", "slash-command-dispatch", "pypi-publish"]:
                result_plan[key] = default_value and not job_exists
            else:
                result_plan[key] = default_value

        generate = any(key != "python_versions" and val is True for key, val in result_plan.items())
        result_plan["generate_workflow"] = generate

        return result_plan

    def update_workflow_config(self, config_manager: ConfigManager, plan: dict) -> None:
        """
        Update workflow configuration settings in the config loader based on the given plan.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            plan: Final workflow plan.
        """
        workflow_settings = {}
        for key in self.workflow_keys:
            workflow_settings[key] = plan.get(key)
        config_manager.config.workflows = config_manager.config.workflows.model_copy(update=workflow_settings)
        logger.info("Config successfully updated with workflow settings")

    def generate_workflow(self, config_manager: ConfigManager) -> None:
        """
        Generate CI/CD files according to the updated configuration settings.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.

        Raises:
            Logs error on failure but does not raise.
        """
        try:
            logger.info("Generating CI/CD files...")

            output_dir = self._get_output_dir()
            workflow_settings = config_manager.get_workflow_settings()
            created_files = self._generate_files(workflow_settings, output_dir)

            if created_files:
                files_list = "\n".join(f" - {f}" for f in created_files)
                logger.info("Successfully generated the following CI/CD files:\n%s", files_list)
            else:
                logger.info("No CI/CD files were generated.")

        except Exception as e:
            logger.error("Error while generating CI/CD files: %s", repr(e), exc_info=True)

    @abstractmethod
    def _get_output_dir(self) -> str:
        """
        Returns the directory path where CI/CD files should be generated for the platform.

        Returns:
            Path to the output directory.
        """
        pass

    @abstractmethod
    def _generate_files(self, workflow_settings, output_dir) -> list[str]:
        """
        Executes the actual generation of CI/CD configuration files.

        Args:
            workflow_settings: workflow specific settings extracted from the config.
            output_dir: The directory to generate the files into.

        Returns:
            List of generated file paths.
        """
        pass


class GitHubWorkflowManager(WorkflowManager):
    """
    Workflow manager implementation for GitHub platform.

    Uses `.github/workflows` directory for workflows storage and generation.
    """

    def _locate_workflow_path(self) -> str | None:
        wdir = os.path.join(self.base_path, ".github", "workflows")
        return wdir if os.path.isdir(wdir) else None

    def _find_existing_jobs(self) -> set[str]:
        if not self.workflow_path:
            return set()

        existing_jobs = set()
        for fname in os.listdir(self.workflow_path):
            if fname.endswith((".yml", ".yaml")):
                fpath = os.path.join(self.workflow_path, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        content = yaml.safe_load(f)
                except (yaml.YAMLError, IOError, OSError) as e:
                    logger.warning(f"Failed to load {fpath}: {e}")
                    continue
                if not content or "jobs" not in content:
                    continue
                existing_jobs.update(content["jobs"].keys())
        return existing_jobs

    def _get_output_dir(self) -> str:
        return os.path.join(self.base_path, ".github", "workflows")

    def _generate_files(self, workflow_settings, output_dir) -> list[str]:
        generator = GitHubWorkflowGenerator(output_dir)
        return generator.generate_selected_jobs(workflow_settings, self.todo_list)


class GitLabWorkflowManager(WorkflowManager):
    """
    Workflow manager implementation for GitLab platform.

    Uses `.gitlab-ci.yml` file at the repository root.
    """

    def _locate_workflow_path(self) -> str | None:
        fpath = os.path.join(self.base_path, ".gitlab-ci.yml")
        if os.path.isfile(fpath):
            return fpath
        return None

    def _find_existing_jobs(self) -> set[str]:
        if not self.workflow_path:
            return set()

        try:
            with open(self.workflow_path, encoding="utf-8") as f:
                content = yaml.safe_load(f)
        except (yaml.YAMLError, IOError, OSError) as e:
            logger.warning(f"Failed to load {self.workflow_path}: {e}")
            return set()

        if not content:
            return set()

        special_keys = {
            "stages",
            "include",
            "variables",
            "default",
            "workflow",
            "image",
            "services",
            "before_script",
            "after_script",
            "cache",
            "pages",
        }

        jobs = {k for k in content.keys() if k not in special_keys and isinstance(content[k], dict)}
        return jobs

    def _get_output_dir(self) -> str:
        return self.base_path

    def _generate_files(self, workflow_settings, output_dir) -> list[str]:
        generator = GitLabWorkflowGenerator(output_dir)
        return generator.generate_selected_jobs(workflow_settings, self.todo_list)


class GitverseWorkflowManager(WorkflowManager):
    """
    Workflow manager implementation for Gitverse platform.

    Tries to use `.gitverse/workflows` directory for workflows, falling back to `.github/workflows`.
    """

    def _locate_workflow_path(self) -> str | None:
        gitverse_dir = os.path.join(self.base_path, ".gitverse", "workflows")
        if os.path.isdir(gitverse_dir):
            return gitverse_dir
        github_dir = os.path.join(self.base_path, ".github", "workflows")
        if os.path.isdir(github_dir):
            return github_dir
        return None

    def _find_existing_jobs(self) -> set[str]:
        if not self.workflow_path:
            return set()

        existing_jobs = set()
        if os.path.isdir(self.workflow_path):
            for fname in os.listdir(self.workflow_path):
                if fname.endswith((".yml", ".yaml")):
                    fpath = os.path.join(self.workflow_path, fname)
                    try:
                        with open(fpath, encoding="utf-8") as f:
                            content = yaml.safe_load(f)
                    except (yaml.YAMLError, IOError, OSError) as e:
                        logger.warning(f"Failed to load {fpath}: {e}")
                        continue
                    if not content or "jobs" not in content:
                        continue
                    existing_jobs.update(content["jobs"].keys())
        return existing_jobs

    def _get_output_dir(self) -> str:
        gitverse_wflows = os.path.join(self.base_path, ".gitverse", "workflows")
        if os.path.isdir(gitverse_wflows):
            return gitverse_wflows
        github_wflows = os.path.join(self.base_path, ".github", "workflows")
        if os.path.isdir(github_wflows):
            return github_wflows
        out_dir = gitverse_wflows
        os.makedirs(out_dir, exist_ok=True)
        return out_dir

    def _generate_files(self, workflow_settings, output_dir) -> list[str]:
        generator = GitHubWorkflowGenerator(output_dir)
        return generator.generate_selected_jobs(workflow_settings, self.todo_list)
