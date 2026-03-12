from typing import List

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.scheduler.workflow_manager import WorkflowManager
from osa_tool.utils.logger import logger


class WorkflowsExecutor:
    """
    Executor for CI/CD workflow generation in the agentic pipeline.

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
        """Disable generation for jobs that already exist in the repository."""
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
