from typing import List

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.scheduler.workflow_manager import WorkflowManager
from osa_tool.utils.logger import logger


class WorkflowsExecutor:
    """
    Executor for orchestrating automated workflow generation and execution within a pipeline, handling sequential and parallel task operations.
    
        Bridges WorkflowManager to the Operation/Executor pattern,
        bypassing the legacy Plan-based config path.
    """


    def __init__(
        self,
        config_manager: ConfigManager,
        workflow_manager: WorkflowManager,
        include_black: bool = True,
        include_tests: bool = True,
        include_pep8: bool = True,
        include_autopep8: bool = False,
        include_fix_pep8: bool = False,
        include_pypi: bool = False,
        pep8_tool: str = "flake8",
        use_poetry: bool = False,
        include_codecov: bool = True,
        python_versions: List[str] = None,
        branches: List[str] = None,
    ):
        """
        Initializes the workflow generator with configuration and feature flags.
        
        Args:
            config_manager: Manages configuration settings for the generator.
            workflow_manager: Manages workflow creation and operations.
            include_black: Flag to include Black code formatting in workflows.
            include_tests: Flag to include test execution in workflows.
            include_pep8: Flag to include PEP 8 style checking in workflows.
            include_autopep8: Flag to include autopep8 automatic formatting in workflows.
            include_fix_pep8: Flag to include attempts to fix PEP 8 violations in workflows.
            include_pypi: Flag to include PyPI publishing steps in workflows.
            pep8_tool: The tool to use for PEP 8 style checking (e.g., 'flake8').
            use_poetry: Flag to use Poetry for dependency management in workflows.
            include_codecov: Flag to include Codecov coverage reporting in workflows.
            python_versions: List of Python versions to test against. Defaults to ['3.9', '3.10'].
            branches: List of git branches to run workflows on. Defaults to ['main', 'master'].
        
        Initializes the following instance attributes:
            config_manager (ConfigManager): Manages configuration settings for the generator.
            workflow_manager (WorkflowManager): Manages workflow creation and operations.
            events (list[OperationEvent]): A list to store operation events.
            _requested (dict): A dictionary containing all requested workflow generation flags and settings, including:
                - generate_workflows (bool): Master flag for workflow generation. Always set to True upon initialization.
                - include_black (bool): Flag for Black code formatting.
                - include_tests (bool): Flag for test execution.
                - include_pep8 (bool): Flag for PEP 8 style checking.
                - include_autopep8 (bool): Flag for autopep8 formatting.
                - include_fix_pep8 (bool): Flag for fixing PEP 8 violations.
                - include_pypi (bool): Flag for PyPI publishing.
                - pep8_tool (str): The PEP 8 checking tool.
                - use_poetry (bool): Flag for using Poetry.
                - include_codecov (bool): Flag for Codecov reporting.
                - python_versions (list[str]): Python versions for testing.
                - branches (list[str]): Git branches for workflows.
        
        Why:
            The `_requested` dictionary centralizes all configuration flags and settings passed to the constructor. This provides a single, consistent source of truth for the workflow generation logic, making it easier to pass these options to other components and to manage the state of what features are enabled. The `generate_workflows` flag is hardcoded to `True` because this executor's purpose is to generate workflows; its presence allows for potential future extension where generation could be toggled.
        """
        self.config_manager = config_manager
        self.workflow_manager = workflow_manager
        self.events: list[OperationEvent] = []
        self._requested = {
            "generate_workflows": True,
            "include_black": include_black,
            "include_tests": include_tests,
            "include_pep8": include_pep8,
            "include_autopep8": include_autopep8,
            "include_fix_pep8": include_fix_pep8,
            "include_pypi": include_pypi,
            "pep8_tool": pep8_tool,
            "use_poetry": use_poetry,
            "include_codecov": include_codecov,
            "python_versions": python_versions or ["3.9", "3.10"],
            "branches": branches or ["main", "master"],
        }

    def generate(self) -> dict:
        """
        Generates a CI/CD workflow based on requested settings.
        
        If the repository contains no Python code, the generation is skipped and a "skipped" event is recorded. Otherwise, the method applies the requested workflow settings, filters out jobs that already exist in the repository to avoid duplication, updates the configuration, and attempts to generate the workflow files. The process logs detailed information and records success or failure events accordingly.
        
        Returns:
            dict: A dictionary with two keys:
                - "result": A dict containing:
                    * "generated" (bool): Whether a workflow was generated (True) or skipped/failed (False).
                    * "settings" (dict, optional): The effective settings used for generation (only present if generation was attempted, i.e., Python code exists). This dictionary reflects the requested settings after filtering out existing jobs.
                - "events" (list): A list of OperationEvent objects recorded during the process, indicating skipped, generated, or failed outcomes with associated data.
        """
        if not self.workflow_manager.has_python_code():
            logger.info("No Python code detected. Skipping workflow generation.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SKIPPED,
                    target="workflows",
                    data={"reason": "no_python_code"},
                )
            )
            return {"result": {"generated": False}, "events": self.events}

        logger.debug("Requested workflow settings: %s", self._requested)
        effective = self._skip_existing_jobs(self._requested)
        logger.debug("Effective workflow settings after filtering: %s", effective)
        WorkflowManager.apply_workflow_settings(self.config_manager, effective)
        success = self.workflow_manager.generate_workflow(self.config_manager)

        if success:
            enabled = [k for k, v in effective.items() if k.startswith("include_") and v is True]
            logger.info("CI/CD workflow generation succeeded. Enabled jobs: %s", enabled)
            self.events.append(
                OperationEvent(
                    kind=EventKind.GENERATED,
                    target="workflows",
                    data={
                        "include_black": effective.get("include_black"),
                        "include_tests": effective.get("include_tests"),
                        "include_pep8": effective.get("include_pep8"),
                        "include_autopep8": effective.get("include_autopep8"),
                        "include_fix_pep8": effective.get("include_fix_pep8"),
                        "include_pypi": effective.get("include_pypi"),
                    },
                )
            )
        else:
            logger.error("CI/CD workflow generation failed. Check previous log messages for details.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.FAILED,
                    target="workflows",
                    data={"reason": "generation_error"},
                )
            )

        return {"result": {"generated": success, "settings": effective}, "events": self.events}

    def _skip_existing_jobs(self, settings: dict) -> dict:
        """
        Disable generation for jobs that already exist in the repository.
        
        This method prevents the tool from regenerating workflow jobs that are already present in the repository, avoiding duplication and unnecessary processing. It checks each job key in the provided settings against the manager's record of existing jobs; if a job already exists, its corresponding setting is set to False, and a warning is logged.
        
        Args:
            settings: A dictionary mapping job keys to boolean values indicating whether each job should be generated.
        
        Returns:
            A modified copy of the input settings dictionary with existing jobs disabled (set to False).
        """
        result = dict(settings)
        for key, job_names in self.workflow_manager.job_name_for_key.items():
            if key not in result:
                continue
            names = [job_names] if isinstance(job_names, str) else job_names
            if any(job in self.workflow_manager.existing_jobs for job in names):
                result[key] = False
                logger.warning("Skipping '%s' workflow: job already exists in the repository.", key)
                self.events.append(
                    OperationEvent(
                        kind=EventKind.SKIPPED,
                        target=key,
                        data={"reason": "already_exists"},
                    )
                )
        return result
