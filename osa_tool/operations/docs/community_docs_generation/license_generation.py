import os

import tomli

from osa_tool.config.settings import ConfigLoader
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root


class LicenseCompiler:
    """
    Compiles and ensures the presence of a LICENSE file in a repository.

    This class is responsible for generating a LICENSE file based on a predefined
    license template and repository metadata. It resolves the target repository
    using SourceRank, checks whether a LICENSE file already exists, and, if not,
    renders and writes the license text to the repository root.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        metadata: RepositoryMetadata,
        license_type: str,
    ):
        self.sourcerank = SourceRank(config_loader)
        self.metadata = metadata
        self.license_type = license_type
        self.license_template_path = os.path.join(osa_project_root(), "docs", "templates", "licenses.toml")

        self.events: list[OperationEvent] = []

    def run(self) -> dict:
        """
        Executes the license compilation process.

        Returns:
        dict: A dictionary containing:
            - 'result': Optional dictionary with 'license' (license type) and 'path' (file path)
            - 'events': List of emitted events during execution

        Raises:
            KeyError: If the specified license_type is not found in the license templates.
        """

        if self.sourcerank.license_presence():
            logger.info("LICENSE file already exists.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.EXISTS,
                    target="LICENSE",
                )
            )
            return self._out(None)

        logger.info("LICENSE was not resolved, compiling started...")

        license_text = self._render_license()
        license_path = os.path.join(self.sourcerank.repo_path, "LICENSE")

        with open(license_path, "w", encoding="utf-8") as f:
            f.write(license_text)

        logger.info("LICENSE has been successfully compiled.")
        self.events.append(
            OperationEvent(
                kind=EventKind.WRITTEN,
                target="LICENSE",
                data={
                    "license": self.license_type,
                    "path": license_path,
                },
            )
        )

        result = {
            "license": self.license_type,
            "path": license_path,
        }

        return self._out(result)

    def _render_license(self) -> str:
        """
        Render the license text based on the selected license type and repository metadata.

        Returns:
            str: The formatted license text.

        Raises:
            KeyError: If the license type does not exist in the templates.
        """
        with open(self.license_template_path, "rb") as f:
            templates = tomli.load(f)

        try:
            return templates[self.license_type]["template"].format(
                year=self.metadata.created_at[:4],
                author=self.metadata.owner,
            )
        except KeyError:
            logger.error(
                f"Couldn't resolve {self.license_type} license type, "
                "try to look up available licenses at documentation."
            )
            raise

    def _out(self, result: dict | None) -> dict:
        """
        Format the standardized operation output.

        Args:
            result (dict | None): Operation result payload.

        Returns:
            dict: Standardized operation output.
        """
        return {
            "result": result,
            "events": self.events,
        }
