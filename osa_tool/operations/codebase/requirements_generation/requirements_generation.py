import subprocess
from pathlib import Path

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class RequirementsGenerator:
    """
    Generates a `requirements.txt` file for a repository using `pipreqs`.

    This class analyzes the source code of the repository to detect imported
    Python packages and produces a dependency list.
    """

    def __init__(self, config_manager: ConfigManager):
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = Path(parse_folder_name(self.repo_url)).resolve()
        self.events: list[OperationEvent] = []

    def generate(self) -> dict:
        logger.info(f"Starting the generation of requirements for: {self.repo_url}")

        if not self._validate_repo_path():
            return {
                "result": None,
                "events": self.events,
            }

        # Scan with notebooks
        try:
            logger.info("Attempting scan with notebooks...")
            self._run_pipreqs(scan_notebooks=True)

            logger.info("Requirements generated successfully with notebook scanning")
            self._add_event(EventKind.GENERATED, mode="scan-notebooks")

            return self._result_dict()

        except subprocess.CalledProcessError as e:
            logger.warning("Standard scan failed. It's likely a Notebook contained invalid syntax.")
            logger.debug(f"Scan error details: {e.stderr or ''}")

            self._add_event(
                EventKind.FAILED,
                mode="scan-notebooks",
                data={"stderr": e.stderr},
            )

        # Scan without notebooks
        logger.info("Retrying requirements generation WITHOUT notebooks...")

        try:
            self._run_pipreqs(scan_notebooks=False)

            logger.info("Requirements generated successfully (excluding notebooks)")
            self._add_event(EventKind.GENERATED, mode="no-notebooks")

            return self._result_dict()

        except subprocess.CalledProcessError as e_retry:
            logger.error("Fatal error: Could not generate requirements even after excluding notebooks.")
            logger.error(f"Final error trace: {e_retry.stderr}")

            self._add_event(
                EventKind.FAILED,
                mode="no-notebooks",
                data={"stderr": e_retry.stderr},
            )

            raise

    def _validate_repo_path(self) -> bool:
        """Check that the repository directory exists."""
        if not self.repo_path.exists():
            logger.error(f"Repo path does not exist: {self.repo_path}")
            self._add_event(
                EventKind.FAILED,
                mode="init",
                data={"error": "repository path does not exist"},
            )
            return False
        return True

    def _run_pipreqs(self, scan_notebooks: bool) -> subprocess.CompletedProcess:
        """Run pipreqs with or without notebook scanning."""
        base_cmd = ["pipreqs", "--force", "--encoding", "utf-8"]
        if scan_notebooks:
            base_cmd.append("--scan-notebooks")

        cmd = base_cmd + [str(self.repo_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        logger.debug(result)
        return result

    def _add_event(self, kind: EventKind, mode: str, data: dict | None = None):
        """Append a structured OperationEvent."""
        payload = {"tool": "pipreqs", "mode": mode}
        if data:
            payload.update(data)

        self.events.append(
            OperationEvent(
                kind=kind,
                target="requirements.txt",
                data=payload,
            )
        )

    def _result_dict(self) -> dict:
        """Return the standard structured result."""
        return {
            "result": {"path": str(self.repo_path / "requirements.txt")},
            "events": self.events,
        }
