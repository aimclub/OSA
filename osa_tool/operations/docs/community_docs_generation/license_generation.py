import os

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root


class LicenseCompiler:
    """
    Handles the compilation and verification of LICENSE files within a repository, ensuring proper licensing documentation is present and correctly formatted.
    
        This class is responsible for generating a LICENSE file based on a predefined
        license template and repository metadata. It resolves the target repository
        using SourceRank, checks whether a LICENSE file already exists, and, if not,
        renders and writes the license text to the repository root.
    """


    def __init__(
        self,
        config_manager: ConfigManager,
        metadata: RepositoryMetadata,
        license_type: str,
    ):
        """
        Initializes a new instance of the LicenseCompiler class.
        
        Args:
            config_manager: Manages configuration settings, used to initialize the SourceRank instance.
            metadata: Contains repository metadata to be stored.
            license_type: The type of license to be used, which determines the template selection.
        
        Initializes the following instance attributes:
            sourcerank (SourceRank): An instance for calculating source rank scores, created using the provided config_manager.
            metadata (RepositoryMetadata): Stores the provided repository metadata.
            license_type (str): Stores the provided license type.
            license_template_path (str): The file system path to the license templates directory. This path is constructed relative to the osa_tool project root to point to "docs/templates/licenses.toml".
            events (list[OperationEvent]): A list to record operation events, initially empty.
        """
        self.sourcerank = SourceRank(config_manager)
        self.metadata = metadata
        self.license_type = license_type
        self.license_template_path = os.path.join(osa_project_root(), "docs", "templates", "licenses.toml")

        self.events: list[OperationEvent] = []

    def run(self) -> dict:
        """
        Executes the license compilation process.
        
        This method checks if a license file already exists in the repository. If it does, it logs an event and returns early. If not, it generates a license file by rendering the appropriate license template with repository metadata (such as year and author), writes the LICENSE file to the repository, logs the action, and returns the result.
        
        Args:
            None: This method uses instance attributes:
                - sourcerank: An object with a `license_presence` method to check for existing license files.
                - license_type: The type of license to generate.
                - metadata: Repository metadata (e.g., creation year, owner) used in rendering the license text.
                - events: A list to which operation events are appended.
        
        Returns:
            dict: A dictionary containing:
                - 'result': Optional dictionary with 'license' (the license type) and 'path' (the file path of the generated license). This is present only if a new license file is created; otherwise, it is None.
                - 'events': List of emitted events during execution (e.g., EXISTS or WRITTEN events).
        
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
        
        The method reads a TOML file containing license templates, selects the appropriate template
        for the current license type, and formats it with specific metadata (year and author).
        This is used to generate the final license file content for the repository.
        
        Args:
            None: Uses instance attributes:
                - license_template_path: Path to the TOML file containing license templates.
                - license_type: The key identifying which license template to use.
                - metadata: An object containing repository metadata, specifically:
                    - created_at: A date string from which the year is extracted.
                    - owner: The author name to be inserted into the license.
        
        Returns:
            str: The formatted license text.
        
        Raises:
            KeyError: If the license type does not exist in the templates, or if the
                      expected template structure is missing.
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
            dict: Standardized operation output containing the operation result and any events collected during the process. This ensures a consistent structure for all operations, facilitating easier logging and downstream processing.
        
        Why:
            This method centralizes the output format for operations, ensuring that every operation returns a dictionary with both the result and any events (like errors or warnings) that occurred. This standardization helps in aggregating and analyzing operation outcomes uniformly across the tool.
        """
        return {
            "result": result,
            "events": self.events,
        }
