import os

import yaml

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.github_workflow import generate_workflows_from_settings
from osa_tool.utils import parse_folder_name, logger


class WorkflowManager:
    """
    Manages GitHub Actions workflows for a given repository.
    Detects existing jobs, builds a plan for workflow generation.
    """

    def __init__(self, base_path: str, sourcerank: SourceRank, metadata: RepositoryMetadata, workflows_plan: dict):
        self.base_path = base_path
        self.sourcerank = sourcerank
        self.metadata = metadata
        self.workflows_plan = workflows_plan
        self.workflows_dir = self._find_workflows_directory()
        self.existing_jobs = self._get_existing_jobs()
        self.excluded_keys = {"workflows_output_dir", "python_versions"}
        self.job_name_for_key = {
            "include_black": ["black", "lint", "Lint", "format"],
            "include_tests": ["test", "unit_tests"],
            "include_pep8": ["lint", "Lint", "pep8_check"],
            "include_autopep8": "autopep8",
            "include_fix_pep8": ["fix_pep8_command", "fix-pep8"],
            "slash-command-dispatch": ["slash_command_dispatch", "slashCommandDispatch"],
            "pypi-publish": ["pypi_publish", "pypi-publish"],
        }

    def _find_workflows_directory(self) -> str | None:
        """Locate the '.github/workflows' directory if it exists."""
        workflows_dir = os.path.join(self.base_path, ".github", "workflows")
        return workflows_dir if os.path.exists(workflows_dir) and os.path.isdir(workflows_dir) else None

    def _has_python_code(self) -> bool:
        """Check whether the repository contains Python code."""
        return "Python" in self.metadata.language

    def _get_existing_jobs(self) -> set[str]:
        """
        Collect the names of all existing jobs from workflow YAML files.

        Returns:
            set[str]: Set of job names defined in existing workflow files.
        """
        existing_jobs = set()
        if not self.workflows_dir:
            return existing_jobs

        for filename in os.listdir(self.workflows_dir):
            if filename.endswith((".yml", ".yaml")):
                file_path = os.path.join(self.workflows_dir, filename)
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        content = yaml.safe_load(f)
                    except (yaml.YAMLError, IOError, OSError) as e:
                        logger.warning(f"Error while loading {file_path}: {e}")
                        continue

                    if not content or "jobs" not in content:
                        continue

                    for job_name in content["jobs"].keys():
                        existing_jobs.add(job_name)

        return existing_jobs

    def build_actual_plan(self) -> dict:
        """
        Build an actual workflow plan based on detected jobs and repository features.

        Returns:
            dict: A dictionary with final workflow plan.
        """
        if not self._has_python_code():
            return {key: False for key in self.workflows_plan}

        result_plan = {}

        for key, default_value in self.workflows_plan.items():
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
                has_tests = self.sourcerank.tests_presence()
                result_plan[key] = default_value and has_tests and not job_exists
            elif key == "include_pep8":
                result_plan[key] = default_value and not job_exists
            elif key in ["include_autopep8", "include_fix_pep8", "slash-command-dispatch", "pypi-publish"]:
                result_plan[key] = default_value and not job_exists
            else:
                result_plan[key] = default_value

        # Set generate_workflows flag if any relevant workflow key is enabled
        generate = any(key not in self.excluded_keys and value is True for key, value in result_plan.items())
        result_plan["generate_workflows"] = generate

        return result_plan


def update_workflow_config(config_loader, plan: dict, workflow_keys: list) -> None:
    """
    Update workflow configuration in the config loader based on the actual plan.

    Args:
        config_loader: Configuration loader object which contains workflow settings
        plan: Workflow plan dictionary.
        workflow_keys: List of workflow keys to update.
    """
    workflow_settings = {}
    for key in workflow_keys:
        workflow_settings[key] = plan.get(key)
    config_loader.config.workflows = config_loader.config.workflows.model_copy(update=workflow_settings)
    logger.info("Config successfully updated with workflow_settings")


def generate_github_workflows(config_loader: ConfigLoader) -> None:
    """
    Generate GitHub Action workflows based on configuration settings.

    Args:
        config_loader: Configuration loader object which contains workflow settings
    """
    try:
        logger.info("Generating GitHub action workflows...")

        # Get the workflow settings from the config
        workflow_settings = config_loader.config.workflows
        repo_url = config_loader.config.git.repository
        output_dir = os.path.join(os.getcwd(), parse_folder_name(repo_url), workflow_settings.output_dir)

        created_files = generate_workflows_from_settings(workflow_settings, output_dir)

        if created_files:
            formatted_files = "\n".join(f" - {file}" for file in created_files)
            logger.info("Successfully generated the following workflow files:\n%s", formatted_files)
        else:
            logger.info("No workflow files were generated.")

    except Exception as e:
        logger.error("Error while generating GitHub workflows: %s", repr(e), exc_info=True)
