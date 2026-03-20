import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import yaml

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.codebase.workflow_generation.workflow_generator import (
    GitHubWorkflowGenerator,
    GitLabWorkflowGenerator,
)
from osa_tool.scheduler.plan import Plan
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.arguments_parser import get_keys_from_group_in_yaml
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class WorkflowManager(ABC):
    """
    Manages workflow automation and pipeline operations for repository analysis and enhancement processes.
    
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

    def __init__(self, repo_url: str, metadata: RepositoryMetadata, args):
        """
        Initializes a new instance of the WorkflowManager.
        
        Args:
            repo_url: The URL of the Git repository.
            metadata: The metadata associated with the repository.
            args: An object containing command-line or configuration arguments, used to extract workflow parameter values.
        
        Initializes the following instance attributes:
            repo_url (str): The URL of the Git repository.
            base_path (str): The local filesystem path where the repository is expected to be cloned. Derived by parsing the repository URL to a folder name and joining it with the current working directory.
            metadata (RepositoryMetadata): The metadata associated with the repository.
            workflow_keys (list): A list of parameter keys defined under the 'workflow' group in the arguments YAML configuration.
            workflow_plan (dict): A dictionary mapping workflow parameter keys to their corresponding values extracted from the provided `args`. Only keys present in `workflow_keys` are included.
            workflow_path (str | None): The absolute path to the directory containing workflow definitions, if found. The method searches first for '.gitverse/workflows', then '.github/workflows' within the base path.
            existing_jobs (set[str]): A set of unique job identifiers found in existing workflow YAML files within the workflow directory. Used to avoid duplication when adding new jobs.
            plan (Optional[Plan]): The execution plan for workflows, initially set to None.
        """
        self.repo_url = repo_url
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(repo_url))
        self.metadata = metadata
        self.workflow_keys = get_keys_from_group_in_yaml("workflow")
        self.workflow_plan = {key: value for key, value in vars(args).items() if key in self.workflow_keys}
        self.workflow_path = self._locate_workflow_path()
        self.existing_jobs = self._find_existing_jobs()
        self.plan: Optional[Plan] = None

    @abstractmethod
    def _locate_workflow_path(self) -> str | None:
        """
        Locate the path where CI/CD configuration files are stored in the repository.
        
        This is an abstract method that must be implemented by subclasses to define how the CI/CD workflow path is discovered for a specific repository structure or platform. It enables the tool to automatically find and analyze CI/CD configurations as part of its documentation and enhancement pipeline.
        
        Returns:
            The path to the CI/CD directory or file if it exists, otherwise None.
        """
        pass

    @abstractmethod
    def _find_existing_jobs(self) -> set[str]:
        """
        Get the set of existing job names defined in CI/CD configurations.
        
        This method is abstract, requiring concrete implementations to define how job names are discovered from the project's CI/CD configuration files (e.g., `.github/workflows/*.yml`, `.gitlab-ci.yml`, or similar). It enables the WorkflowManager to identify which jobs already exist, preventing duplication and ensuring new jobs are added appropriately.
        
        Returns:
            Set of job names.
        """
        pass

    def has_python_code(self) -> bool:
        """
        Checks whether the repository contains Python code.
        
        First checks the repository metadata language field. If that is absent or
        does not mention Python, falls back to counting ``.py`` files on disk.
        
        This two‑step approach ensures detection even when repository metadata is incomplete or inaccurate.
        
        Returns:
            True if Python code is present, False otherwise.
        """
        if self.metadata.language and "Python" in self.metadata.language:
            return True

        py_count = sum(1 for _ in Path(self.base_path).rglob("*.py"))
        if py_count > 0:
            logger.info("Metadata did not report Python, but found %d .py file(s) on disk.", py_count)
            return True

        return False

    def build_actual_plan(self, sourcerank: SourceRank) -> dict:
        """
        Build the workflow generation plan based on the initial plan, Python presence, existing jobs, and platform-specific logic.
        
        This method determines which workflow jobs should be generated for the repository. It first checks if the repository contains Python code; if not, all plan entries are set to False. For each planned job, it checks whether a job with the same name already exists in the repository. The final decision for each job combines the default plan value, the presence of Python code, and, for certain jobs, additional conditions like test detection. The method also sets a 'generate_workflow' flag indicating whether any job (except python_versions) is enabled.
        
        Args:
            sourcerank: Analyzer object used to detect the presence of tests in the repository.
        
        Returns:
            Dictionary representing the final workflow plan. Keys correspond to job identifiers (e.g., 'include_tests', 'include_black'), and values are booleans indicating whether the job should be generated. Includes an additional key 'generate_workflow' that is True if any job (other than 'python_versions') is enabled.
        
        Why:
        - The plan is only built if Python code is present because the workflows are Python-specific.
        - Jobs are skipped if they already exist in the repository to avoid duplicates.
        - Special logic for 'include_tests' requires both the default plan and actual test detection to be true.
        - The 'generate_workflow' flag helps downstream steps decide whether to proceed with workflow file generation.
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

    @staticmethod
    def apply_workflow_settings(config_manager: ConfigManager, settings: dict) -> None:
        """
        Apply workflow settings directly from a dict, bypassing the legacy Plan.
        Used by the agentic pipeline to update workflow configurations without using the older Plan-based system.
        
        Args:
            config_manager: Configuration manager to update. Its internal workflow configuration will be replaced.
            settings: Dict of workflow settings keys and values. These are applied directly to update the existing workflows configuration.
        
        Why:
            This method provides a direct path to update workflow settings, avoiding the overhead and constraints of the legacy Plan system. It is specifically designed for the agentic pipeline, which requires dynamic and immediate configuration updates.
        """
        config_manager.config.workflows = config_manager.config.workflows.model_copy(update=settings)
        logger.info("Config successfully updated with workflow settings")

    def update_workflow_config(self, config_manager: ConfigManager, plan: Plan) -> None:
        """
        Update workflow configuration settings in the config loader based on the given plan.
        
        This method transfers relevant workflow settings from the finalized plan into the configuration manager. It ensures that the runtime configuration reflects the workflow preferences and parameters defined in the plan, allowing subsequent operations to use the correct settings.
        
        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            plan: Final workflow plan containing the workflow keys and their intended values.
        
        Why:
            The plan contains the user-defined or generated workflow preferences (e.g., steps, modes, or options). These settings need to be applied to the configuration manager so that other components in the system can access and use the updated workflow configuration during execution.
        """
        self.plan = plan
        workflow_settings = {}
        for key in self.workflow_keys:
            workflow_settings[key] = plan.get(key)
        config_manager.config.workflows = config_manager.config.workflows.model_copy(update=workflow_settings)
        logger.info("Config successfully updated with workflow settings")

    def generate_workflow(self, config_manager: ConfigManager) -> bool:
        """
        Generate CI/CD workflow files according to the updated configuration settings.
        
        This method creates GitHub Actions workflow files in a project-specific directory (`.gitverse/workflows` by default, falling back to `.github/workflows` if needed). It uses the stored execution plan to produce only the jobs selected by the user, ensuring generated workflows align with the user's preferences without interfering with existing configurations.
        
        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
        
        Returns:
            True if at least one workflow file was successfully generated; False if no files were created or if an error occurred.
        
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
                return False
        except Exception as e:
            logger.error("Error while generating CI/CD files: %s", repr(e), exc_info=True)
            return False
        return True

    @abstractmethod
    def _get_output_dir(self) -> str:
        """
        Returns the directory path where CI/CD workflow files should be generated for the specific platform.
        
        This is an abstract method that must be implemented by subclasses to define the platform-specific output location for CI/CD configuration files (e.g., `.github/workflows/` for GitHub, `.gitlab-ci.yml` for GitLab). The method ensures that generated CI/CD files are placed in the correct, platform-standard directory.
        
        Returns:
            Path to the output directory as a string. The path should be relative to the repository root and follow the conventions of the target CI/CD platform.
        """
        pass

    @abstractmethod
    def _generate_files(self, workflow_settings, output_dir) -> list[str]:
        """
        Executes the actual generation of CI/CD configuration files.
        
        This is an abstract method that must be implemented by subclasses to produce the actual CI/CD configuration files (e.g., for GitHub Actions, GitLab CI, etc.) based on the provided workflow settings.
        
        Args:
            workflow_settings: Workflow-specific settings extracted from the configuration. These settings determine the content and structure of the generated CI/CD files.
            output_dir: The directory where the generated configuration files will be written.
        
        Returns:
            List of generated file paths. Each path should be relative or absolute, indicating where each configuration file was created.
        """
        pass


class GitHubWorkflowManager(WorkflowManager):
    """
    Manages and orchestrates GitHub Actions workflows for automated repository operations and pipeline execution.
    
        Uses `.github/workflows` directory for workflows storage and generation.
    """


    def _locate_workflow_path(self) -> str | None:
        """
        Locates the path to the GitHub workflows directory within the base path.
        
        This method constructs the expected directory path for `.github/workflows` relative to the instance's `base_path` and checks if it exists as a directory. It is used internally to determine whether the repository contains a GitHub Actions workflows directory before performing related operations.
        
        Args:
            self: The instance of GitHubWorkflowManager, which provides the `base_path` attribute.
        
        Returns:
            str | None: The absolute path to the `.github/workflows` directory if it exists, otherwise None.
        """
        wdir = os.path.join(self.base_path, ".github", "workflows")
        return wdir if os.path.isdir(wdir) else None

    def _find_existing_jobs(self) -> set[str]:
        """
        Scans the workflow directory to identify and collect names of existing jobs defined in YAML files.
        
        This method iterates through all files in the directory specified by the workflow path, parses valid YAML files, and extracts the keys from the 'jobs' section of each file. It is used to gather existing job names to avoid duplication when generating new workflow jobs.
        
        Args:
            self: The instance of the class.
        
        Returns:
            set[str]: A set of unique job names found across all processed workflow files. Returns an empty set if the workflow path is not set or if no valid jobs are found.
        
        Why:
            This method ensures that new jobs generated by the tool do not conflict with existing job names in the repository's GitHub Actions workflows, preventing naming collisions and workflow errors.
        """
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
        """
        Constructs the file path for the output directory where GitHub workflows are stored.
        This directory is the standard location for GitHub Actions workflow files within a repository.
        
        Args:
            self: The instance of GitHubWorkflowManager, which provides the base path.
        
        Returns:
            str: The full path to the .github/workflows directory within the base path.
        """
        return os.path.join(self.base_path, ".github", "workflows")

    def _generate_files(self, workflow_settings, output_dir) -> list[str]:
        """
        Generates workflow files based on the provided settings and the current execution plan.
        
        This method delegates the actual file generation to a GitHubWorkflowGenerator instance, using the stored execution plan from the manager along with the provided settings. The purpose is to separate the workflow management logic from the file creation details.
        
        Args:
            workflow_settings: An object containing the configuration and preferences for workflow generation.
            output_dir: The directory path where the generated files will be saved.
        
        Returns:
            list[str]: A list of file paths for the newly created workflow files.
        """
        generator = GitHubWorkflowGenerator(output_dir)
        return generator.generate_selected_jobs(workflow_settings, self.plan)


class GitLabWorkflowManager(WorkflowManager):
    """
    GitLabWorkflowManager orchestrates automated workflows for repository analysis, documentation generation, and structural enhancements within GitLab-hosted projects. It manages pipelines for content validation, multi-language translation, and systematic repository improvements to ensure consistent documentation quality and maintainability.
    
        Uses `.gitlab-ci.yml` file at the repository root.
    """


    def _locate_workflow_path(self) -> str | None:
        """
        Locates the path to the GitLab CI workflow file within the base directory.
        
        The method checks for the existence of a '.gitlab-ci.yml' file at the location
        defined by the instance's base path. This is used to find the CI configuration
        so that subsequent operations (like validation or updates) can be performed on it.
        
        Returns:
            str | None: The absolute path to the GitLab CI configuration file if it exists,
                otherwise None.
        """
        fpath = os.path.join(self.base_path, ".gitlab-ci.yml")
        if os.path.isfile(fpath):
            return fpath
        return None

    def _find_existing_jobs(self) -> set[str]:
        """
        Parses the workflow file to identify and return a set of existing job names.
        
        This method reads the YAML file specified by the workflow path, filters out 
        predefined top-level keywords (such as stages, include, and variables), 
        and identifies keys that represent job definitions. It is used to understand
        the current job structure of a GitLab CI/CD configuration, which is necessary
        for operations like adding new jobs without overwriting existing ones.
        
        Args:
            self: The instance of the class.
        
        Returns:
            set[str]: A set of strings containing the names of the jobs found in the workflow file.
            Returns an empty set if the workflow path is not set, the file cannot be loaded,
            the YAML content is empty, or if no job definitions are found.
        
        Note:
            The method filters out the following special top-level keys that are not jobs:
            stages, include, variables, default, workflow, image, services, before_script,
            after_script, cache, pages. A key is considered a job only if its value is a dictionary.
        """
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
        """
        Retrieves the base directory path for output.
        
        This method provides a consistent, centralized way to access the base output directory
        configured for the workflow. It ensures that all output files are stored in a single,
        predictable location, which simplifies file management and path construction throughout
        the pipeline.
        
        Args:
            self: The instance of the class.
        
        Returns:
            str: The base path where output files are stored. This is the value of `self.base_path`.
        """
        return self.base_path

    def _generate_files(self, workflow_settings, output_dir) -> list[str]:
        """
        Generates workflow files based on the provided settings and the current plan.
        This method creates a GitLabWorkflowGenerator instance and delegates the actual file generation to it, returning the resulting file paths.
        
        Args:
            workflow_settings: An object containing the configuration and settings for workflow generation.
            output_dir: The directory path where the generated files will be saved.
        
        Returns:
            list[str]: A list of file paths for the generated GitLab workflow files.
        """
        generator = GitLabWorkflowGenerator(output_dir)
        return generator.generate_selected_jobs(workflow_settings, self.plan)


class GitverseWorkflowManager(WorkflowManager):
    """
    GitverseWorkflowManager orchestrates automated repository analysis and enhancement workflows, managing documentation generation, content validation, and structural improvements across open-source projects.
    
        Tries to use `.gitverse/workflows` directory for workflows, falling back to `.github/workflows`.
    """


    def _locate_workflow_path(self) -> str | None:
        """
        Locates the directory path containing workflow definitions within the base path.
        
        The method checks for the existence of a '.gitverse/workflows' directory first, followed by a '.github/workflows' directory. It returns the path to the first one found. This order prioritizes Gitverse-specific workflows over standard GitHub workflows, allowing for custom workflow definitions when present.
        
        Args:
            self: The instance of the GitverseWorkflowManager.
        
        Returns:
            str | None: The absolute path to the workflows directory if found, otherwise None.
        """
        gitverse_dir = os.path.join(self.base_path, ".gitverse", "workflows")
        if os.path.isdir(gitverse_dir):
            return gitverse_dir
        github_dir = os.path.join(self.base_path, ".github", "workflows")
        if os.path.isdir(github_dir):
            return github_dir
        return None

    def _find_existing_jobs(self) -> set[str]:
        """
        Scans the workflow directory to identify and collect names of existing jobs.
        
        This method iterates through all YAML files within the directory specified by the
        workflow path, parses their content, and extracts the keys defined under the
        'jobs' section of each workflow. It is used to understand which jobs are already
        defined in the repository's CI/CD workflows, which helps avoid duplication when
        adding new jobs.
        
        Args:
            self: The instance of the class.
        
        Returns:
            set[str]: A set of unique job identifiers found across all valid workflow files.
            If the workflow path is not set, an empty set is returned.
            If a YAML file cannot be parsed or lacks a 'jobs' section, it is skipped.
        """
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
        """
        Determines the appropriate directory for storing workflow files.
        
        The method checks for the existence of a '.gitverse/workflows' directory within the base path. If it does not exist, it checks for '.github/workflows'. If neither exists, it creates the '.gitverse/workflows' directory and returns its path.
        
        This prioritizes a project-specific `.gitverse/workflows` directory over the conventional `.github/workflows` directory to allow for custom workflow management without interfering with existing GitHub Actions configurations.
        
        Args:
            self: The instance of the GitverseWorkflowManager class.
        
        Returns:
            str: The absolute path to the output directory for workflows.
        """
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
        """
        Generates workflow files based on the provided settings and the current execution plan.
        This method creates GitHub Actions workflow files by delegating to a specialized generator, which uses the stored execution plan to produce only the jobs selected by the user.
        
        Args:
            workflow_settings: An object containing the configuration and preferences for workflow generation.
            output_dir: The directory path where the generated files will be saved.
        
        Returns:
            list[str]: A list of file paths for the newly created workflow files.
        """
        generator = GitHubWorkflowGenerator(output_dir)
        return generator.generate_selected_jobs(workflow_settings, self.plan)
