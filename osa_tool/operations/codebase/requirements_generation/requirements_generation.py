import subprocess
from pathlib import Path

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import parse_folder_name
from pydantic import BaseModel


class MergedRequirements(BaseModel):
    """
    A class that merges multiple requirement specifications into a single unified set.
    
        Class Attributes:
        - dependencies: A list of dependency objects that have been merged.
    
        Methods:
        - __init__: Initializes the MergedRequirements instance with a list of requirement sources.
        - merge: Combines the provided requirement sources into a single set of dependencies.
        - validate: Checks the merged dependencies for conflicts or inconsistencies.
        - export: Outputs the merged dependencies in a specified format.
    
        Attributes:
        - sources: The original requirement sources provided during initialization.
        - merged_deps: The consolidated list of dependencies after merging.
        - conflicts: Any identified conflicts between requirements, stored after validation.
    
        The class processes multiple requirement inputs, resolves overlaps, and produces a clean, unified dependency list suitable for further use or export.
    """

    dependencies: list[str]


class RequirementsGenerator:
    """
    Generates a `requirements.txt` file by analyzing the project's source code to identify and list its Python dependencies.
    
        This class analyzes the source code of the repository to detect imported
        Python packages and produces a dependency list.
    """


    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the RequirementsGenerator instance with configuration and sets up repository and model handling.
        
        This constructor prepares the components needed for generating repository documentation and requirements by loading configuration settings, extracting repository information, and initializing the model handler for AI-powered operations.
        
        Args:
            config_manager: The configuration manager instance used to retrieve all settings.
        
        Class Fields:
            config_manager (ConfigManager): Configuration manager instance for accessing settings.
            repo_url (str): URL of the Git repository extracted from the git settings.
            repo_path (Path): Resolved filesystem path for the repository folder, derived by parsing the repository URL to a safe folder name.
            events (list[OperationEvent]): List to store operation events for tracking and logging.
            prompts (PromptLoader): Loader for prompt templates used in documentation generation.
            model_handler (ModelHandler): Model handler instance built from the configuration, enabling AI model interactions.
        """
        self.config_manager = config_manager
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = Path(parse_folder_name(self.repo_url)).resolve()
        self.events: list[OperationEvent] = []
        self.prompts = self.config_manager.get_prompts()
        self.model_handler = ModelHandlerFactory.build(self.config_manager.config)

    def generate(self) -> dict:
        """
        Generates Python dependencies for a repository using pipreqs.
        
        Attempts to generate a requirements.txt file by scanning the repository, first including Jupyter notebooks, then falling back to scanning without notebooks if the first attempt fails. If an existing requirements.txt or pyproject.toml file exists, it preserves the existing dependency versions and uses LLM refinement to merge newly generated requirements with the old context.
        
        The process ensures that dependency lists are consolidated and free of duplicates, maintaining existing version constraints where possible. This is important for reproducibility and environment setup, especially in projects that use Jupyter notebooks for development or examples.
        
        Args:
            self: The RequirementsGenerator instance.
        
        Returns:
            dict: A structured result containing the generation outcome and events. The dictionary includes:
                - "result": A dictionary containing the "path" to the generated 'requirements.txt' file.
                - "events": The list of event dictionaries recorded during the generation process.
        
        Raises:
            subprocess.CalledProcessError: If both scanning attempts (with and without notebooks) fail, the exception from the final attempt is raised.
        """
        logger.info(f"Starting the generation of requirements for: {self.repo_url}")
        if not self._validate_repo_path():
            return {
                "result": None,
                "events": self.events,
            }

        req_file_path = self.repo_path / "requirements.txt"
        pyproject_path = self.repo_path / "pyproject.toml"

        old_context = self._get_existing_context(req_file_path, pyproject_path)
        if old_context:
            self._add_event(EventKind.ANALYZED, mode="existing-context")

        # Scan with notebooks
        try:
            logger.info("Attempting scan with notebooks...")
            self._run_pipreqs(scan_notebooks=True)
            logger.info("Requirements generated successfully with notebook scanning")
            self._add_event(EventKind.GENERATED, mode="scan-notebooks")

        except subprocess.CalledProcessError as e:
            logger.warning("Standard scan failed. Retrying without notebooks...")
            self._add_event(EventKind.FAILED, mode="scan-notebooks", data={"stderr": e.stderr})

            # Scan without notebooks
            logger.info("Retrying requirements generation WITHOUT notebooks...")
            try:
                self._run_pipreqs(scan_notebooks=False)
                logger.info("Requirements generated successfully (excluding notebooks)")
                self._add_event(EventKind.GENERATED, mode="no-notebooks")

            except subprocess.CalledProcessError as e_retry:
                logger.error("Fatal error: Could not generate requirements.")
                self._add_event(EventKind.FAILED, mode="no-notebooks", data={"stderr": e_retry.stderr})
                raise

        # LLM Refinement
        if old_context:
            logger.info("Merging requirements versions using LLM...")
            self._refine_with_llm(req_file_path, old_context)

        return self._result_dict()

    def _refine_with_llm(self, req_file_path: Path, old_context: str) -> None:
        """
        Refines the contents of a requirements file by merging existing and new dependencies using an LLM.
        
        The method reads new requirements from the given file, combines them with the old requirements context via a prompt to an LLM, and writes back a merged, deduplicated list. This ensures that dependency lists are consolidated and free of duplicates without manual editing.
        
        Args:
            req_file_path: Path to the requirements file to be updated.
            old_context: The existing requirements text (or context) to merge with the new requirements.
        
        Why:
        - The LLM is prompted to produce a unified list of dependencies, removing duplicates and organizing the output.
        - JSON parsing via Pydantic ensures the LLM response is structured and validated before being used.
        - If the LLM returns an empty or invalid response, the file is not overwritten and a warning is logged.
        
        The method logs an event on successful refinement and handles errors gracefully, logging any exceptions encountered.
        """
        try:
            new_requirements = req_file_path.read_text(encoding="utf-8").strip()
            if not new_requirements:
                return

            prompt_template = self.prompts.get("requirements.merge_requirements")
            prompt = PromptBuilder.render(
                prompt_template, old_requirements=old_context, new_requirements=new_requirements
            )
            response: MergedRequirements = self.model_handler.send_and_parse(prompt, MergedRequirements)
            if response and response.dependencies:
                merged_content = "\n".join(response.dependencies).strip()

                req_file_path.write_text(merged_content, encoding="utf-8")
                logger.info("Requirements successfully refined with LLM (JSON parsed).")
                self._add_event(EventKind.REFINED, mode="llm-merge")
            else:
                logger.warning("LLM returned an empty dependency list.")

        except Exception as e:
            logger.error(f"Error during LLM refinement: {e}")

    def _get_existing_context(self, req_path: Path, pyproject_path: Path) -> str:
        """
        Reads existing dependency files to preserve version information for context.
        
        This method collects the content of existing dependency files to provide context
        for subsequent operations, such as generating new requirements while maintaining
        current version constraints. It reads both `requirements.txt` and `pyproject.toml`
        if they exist, and formats their contents into a single string with clear section
        headers. If a file cannot be read, a warning is logged but the process continues.
        
        Args:
            req_path: Path to the `requirements.txt` file.
            pyproject_path: Path to the `pyproject.toml` file.
        
        Returns:
            A string containing the formatted contents of the existing dependency files,
            with each file's content preceded by a header. Returns an empty string if
            neither file exists or both are empty/unreadable.
        """
        context = ""
        if req_path.exists():
            try:
                content = req_path.read_text(encoding="utf-8").strip()
                if content:
                    context += f"--- EXISTING REQUIREMENTS.TXT ---\n{content}\n"
            except Exception as e:
                logger.warning(f"Could not read requirements.txt: {e}")

        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8").strip()
                if content:
                    context += f"--- EXISTING PYPROJECT.TOML ---\n{content}\n"
            except Exception as e:
                logger.warning(f"Could not read pyproject.toml: {e}")

        return context.strip()

    def _validate_repo_path(self) -> bool:
        """
        Check that the repository directory exists.
        
        This validation ensures the provided `repo_path` points to an actual directory on the filesystem before proceeding with further operations. If the path does not exist, an error is logged and a failure event is recorded to track the initialization issue.
        
        Returns:
            True if the repository directory exists; False otherwise, which signals a validation failure.
        """
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
        """
        Run pipreqs to generate requirements.txt from Python dependencies, optionally scanning Jupyter notebooks.
        
        This method executes the pipreqs command-line tool to analyze the repository's Python files and
        automatically generate a requirements.txt file. It can be configured to include dependencies
        found within Jupyter notebooks (.ipynb files) when scanning is enabled.
        
        Args:
            scan_notebooks: If True, includes the `--scan-notebooks` flag to extend dependency
                            detection to Jupyter notebooks in the repository. If False, only
                            standard Python files are analyzed.
        
        Returns:
            A CompletedProcess instance representing the result of the subprocess run,
            containing attributes like stdout, stderr, and returncode. This allows the
            caller to inspect the command output and execution status.
        
        Why:
            Automating requirements generation ensures that the project's dependencies are
            consistently captured and documented, which is essential for reproducibility
            and environment setup. The option to scan notebooks accommodates projects that
            use Jupyter notebooks for development or examples, ensuring their dependencies
            are not overlooked.
        """
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
        """
        Append a structured OperationEvent to the internal events list.
        
        This method constructs a standardized event payload for tracking operations performed
        by the pipreqs tool, then creates an OperationEvent record. It is used internally
        to log actions and outcomes during requirements generation, enabling later analysis
        or reporting of the tool's activities.
        
        Args:
            kind: The category or type of event being recorded (e.g., info, warning, error).
            mode: The operational mode in which the event occurred, describing the context
                  or phase of the requirements generation process.
            data: Optional additional key-value data to include in the event payload.
                  If provided, this data is merged into the base payload.
        
        The event is always associated with the target file "requirements.txt" and includes
        a base payload identifying the tool as "pipreqs" along with the specified mode.
        """
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
        """
        Return the standard structured result dictionary used by the RequirementsGenerator.
        
        This method constructs a consistent dictionary format that includes:
        - The generated requirements file path.
        - A log of events that occurred during the requirements generation process.
        
        Args:
            self: The RequirementsGenerator instance.
        
        Returns:
            A dictionary with two keys:
                - "result": A dictionary containing the "path" to the generated 'requirements.txt' file.
                - "events": The list of event dictionaries recorded during the generation process.
        """
        return {
            "result": {"path": str(self.repo_path / "requirements.txt")},
            "events": self.events,
        }
