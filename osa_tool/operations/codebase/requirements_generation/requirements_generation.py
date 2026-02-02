import subprocess
from pathlib import Path

from osa_tool.config.settings import ConfigLoader
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class RequirementsGenerator:
    """
    Generates a `requirements.txt` file for a repository using `pipreqs`.

    This class analyzes the source code of the repository to detect imported
    Python packages and produces a dependency list.
    """

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader.config
        self.repo_url = self.config.git.repository
        self.repo_path = Path(parse_folder_name(self.repo_url)).resolve()
        self.events: list[OperationEvent] = []

    def generate(self) -> dict:
        """
        Generate `requirements.txt` for the repository.

        Runs `pipreqs` against the repository directory, captures the result,
        and emits structured operation events describing success or failure.

        Returns:
            dict: A result dictionary containing:
                - result: Metadata about the generated file.
                - events: A list of `OperationEvent` objects produced during execution.

        Raises:
            subprocess.CalledProcessError: If `pipreqs` execution fails.
        """

        logger.info("Starting requirements generation")

        try:
            result = subprocess.run(
                ["pipreqs", "--scan-notebooks", "--force", "--encoding", "utf-8", str(self.repo_path)],
                capture_output=True,
                text=True,
                check=True,
            )

            self.events.append(
                OperationEvent(
                    kind=EventKind.GENERATED,
                    target="requirements.txt",
                    data={"tool": "pipreqs"},
                )
            )

            logger.info("Requirements generated successfully")
            logger.debug(result)

            return {
                "result": {"path": str(self.repo_path / "requirements.txt")},
                "events": self.events,
            }

        except subprocess.CalledProcessError as e:
            self.events.append(
                OperationEvent(
                    kind=EventKind.FAILED,
                    target="requirements.txt",
                    data={"stderr": e.stderr},
                )
            )
            raise
