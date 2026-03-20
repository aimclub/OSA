import os

from langchain_core.output_parsers import PydanticOutputParser
from pydantic import ValidationError

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import OperationEvent
from osa_tool.operations.analysis.repository_report.response_validation import (
    RepositoryReport,
    RepositoryStructure,
    ReadmeEvaluation,
    CodeDocumentation,
    OverallAssessment,
    AfterReportBlock,
    AfterReport,
    AfterReportSummary,
    AfterReportBlocksPlan,
)
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor, JsonParseError
from osa_tool.utils.utils import extract_readme_content, parse_folder_name


class TextGenerator:
    """
    TextGenerator generates repository analysis text using AI models.
    
        This class initializes with configuration and repository metadata, then uses
        a model handler to generate comprehensive repository analysis based on
        file presence, structure, and other repository characteristics.
    
        Attributes:
            config_manager: Configuration manager providing settings and prompts.
            model_settings: Model settings for general tasks.
            sourcerank: SourceRank instance for analysis.
            prompts: Prompt loader for templates.
            metadata: Repository metadata.
            model_handler: Model handler built from general model settings.
            repo_url: URL of the Git repository.
            base_path: Local base path derived from the repository URL.
    
        Methods:
            __init__: Initializes the class with configuration and repository metadata.
            make_request: Sends a request to generate repository analysis.
            _extract_presence_files: Extracts information about key files in the repository.
    """

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        """
        Initializes the TextGenerator instance with configuration and repository metadata.
        
        Args:
            config_manager: Configuration manager providing settings and prompts.
            metadata: Metadata about the repository.
        
        Initializes the following class fields:
            config_manager: Configuration manager instance.
            model_settings: Model settings for general tasks, retrieved from the config manager.
            sourcerank: SourceRank instance for repository analysis.
            prompts: Prompt loader for accessing and managing template prompts.
            metadata: Repository metadata provided as input.
            model_handler: Model handler built from the general model settings, used for LLM interactions.
            repo_url: URL of the Git repository, obtained from the git settings in the configuration.
            base_path: Local base path where the repository would be cloned, derived by joining the current working directory with a folder name parsed from the repository URL. This path is used for local file operations.
        
        The initialization sets up all necessary components for the TextGenerator to perform documentation generation and repository analysis tasks, ensuring it has access to configuration, models, prompts, and repository-specific information.
        """
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("general")
        self.sourcerank = SourceRank(self.config_manager)
        self.prompts = self.config_manager.get_prompts()
        self.metadata = metadata
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.repo_url = self.config_manager.get_git_settings().repository
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

    def make_request(self) -> RepositoryReport:
        """
        Sends a request to the model handler to generate a structured repository analysis.
        
        This method constructs a detailed prompt using repository metadata, source tree, presence of key files, and README content. It then sends this prompt to the LLM via the model handler, which attempts to parse the response into a validated `RepositoryReport` object. If parsing fails due to JSON or validation errors, a fallback empty report is returned to ensure graceful degradation. Any other unexpected error is raised.
        
        Args:
            None: This method uses instance attributes (e.g., `self.prompts`, `self.metadata`, `self.sourcerank.tree`) to gather all necessary data.
        
        Returns:
            RepositoryReport: The structured analysis of the repository. On successful parsing, this is the validated report from the model. If parsing fails, a fallback empty `RepositoryReport` is returned to prevent complete failure of the analysis pipeline.
        """
        prompt = PromptBuilder.render(
            self.prompts.get("analysis.main_prompt"),
            project_name=self.metadata.name,
            metadata=self.metadata,
            repository_tree=self.sourcerank.tree,
            presence_files=self._extract_presence_files(),
            readme_content=extract_readme_content(self.base_path),
        )

        try:
            data = self.model_handler.send_and_parse(
                prompt=prompt,
                parser=lambda raw: RepositoryReport.model_validate(JsonProcessor.parse(raw, expected_type=dict)),
            )
            return data

        except (ValidationError, JsonParseError) as e:
            logger.warning(f"Parsing failed, fallback applied: {e}")

            return RepositoryReport(
                structure=RepositoryStructure(),
                readme=ReadmeEvaluation(),
                documentation=CodeDocumentation(),
                assessment=OverallAssessment(),
            )

        except Exception as e:
            logger.error(f"Unexpected error while parsing RepositoryReport: {e}")
            raise ValueError(f"Failed to process model response: {e}")

    def _extract_presence_files(self) -> list[str]:
        """
        Extracts information about the presence of key files in the repository.
        
        This method generates a list of human-readable strings indicating whether key files like
        README, LICENSE, documentation, examples, and requirements are present. Each string
        reports the presence status (e.g., "README presence is True") by querying the associated
        SourceRank helper methods. This information is used to summarize the repository's
        documentation and support file completeness, which contributes to overall project
        assessment.
        
        Returns:
            list[str]: A list of strings, each describing the presence status of a specific
                       key file type. The order is: README, LICENSE, examples, documentation,
                       and requirements.
        """
        contents = [
            f"README presence is {self.sourcerank.readme_presence()}",
            f"LICENSE presence is {self.sourcerank.license_presence()}",
            f"Examples presence is {self.sourcerank.examples_presence()}",
            f"Documentation presence is {self.sourcerank.docs_presence()}",
            f"Requirements presence is {self.sourcerank.requirements_presence()}",
        ]
        return contents


class AfterReportTextGenerator:
    """
    AfterReportTextGenerator generates a summary report text after a series of tasks have been completed. It utilizes a model handler to process task data and results into a coherent narrative summary.
    
        Class Attributes:
            config_manager: Configuration manager for accessing settings and prompts.
            model_settings: Model settings for general tasks.
            prompts: Loader for prompt templates.
            completed_tasks: List of completed tasks with their statuses.
            task_results: Dictionary containing results of previous tasks.
            model_handler: Model handler instance for processing tasks.
    
        The `__init__` method initializes the class instance with the necessary configuration, task data, and model handler. The `make_request` method sends a request to the model handler to generate the final OSA work summary. The `_events_to_text` method converts a list of operation events into a formatted string. The `_operations_to_text` method converts the completed tasks and their results into a formatted text report for use in the summary generation.
    """

    def __init__(
        self,
        config_manger: ConfigManager,
        completed_tasks: list[tuple[str, bool]],
        task_results: dict[str, dict] | None = None,
    ) -> None:
        """
        Initializes the AfterReportTextGenerator instance with configuration, task data, and model handler.
        
        Args:
            config_manger: Configuration manager for accessing settings and prompts.
            completed_tasks: List of completed tasks, where each task is represented as a tuple containing the task name and its completion status (True/False).
            task_results: Optional dictionary containing the results of previous tasks, keyed by task name. If not provided, defaults to an empty dictionary.
        
        Initializes the following class fields:
            config_manager (ConfigManager): The provided configuration manager instance.
            model_settings (ModelSettings): Model settings for general tasks, retrieved from the configuration manager.
            prompts (PromptLoader): Loader for prompt templates, retrieved from the configuration manager.
            completed_tasks (list[tuple[str, bool]]): The provided list of completed tasks with their statuses.
            task_results (dict[str, dict]): Dictionary containing results of previous tasks; defaults to an empty dict if the argument is None.
            model_handler (ModelHandler): A ModelHandler instance, built via the ModelHandlerFactory using the retrieved general model settings. This handler is responsible for processing tasks that generate the after-report text.
        """
        self.config_manager = config_manger
        self.model_settings = self.config_manager.get_model_settings("general")
        self.prompts = self.config_manager.get_prompts()
        self.completed_tasks = completed_tasks
        self.task_results = task_results or {}
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)

    def make_request(self) -> AfterReport:
        """
        Sends a request to the model handler to generate the OSA work summary.
        
                This method orchestrates the generation of an AfterReport by:
                1. Converting completed tasks and their results into a formatted text representation.
                2. Using two separate LLM chains to produce structured outputs:
                   - A summary (AfterReportSummary) of the overall work.
                   - A plan for organizing the summary into blocks (AfterReportBlocksPlan).
                3. Processing the block plan to attach task completion status and constructing the final AfterReport.
        
                Args:
                    None. The method uses instance attributes:
                        self.completed_tasks: A list of tuples (task_name, performed_bool).
                        self.task_results: A dictionary mapping task names to result details.
                        self.prompts: A dictionary containing prompt templates.
                        self.model_handler: The handler for executing LLM chains.
        
                Returns:
                    AfterReport: An object containing:
                        summary: The generated overall summary from the model.
                        blocks: A list of AfterReportBlock objects, each with a name, description, and list of tasks (with completion status).
        
                Raises:
                    ValueError: If an error occurs during model response processing or LLM chain execution. The original exception is logged and chained.
        """
        performed_lookup = {name: done for name, done in self.completed_tasks}
        operations_text = self._operations_to_text(self.completed_tasks, self.task_results)

        try:
            # Summary (structured JSON -> AfterReportSummary)
            summary_parser = PydanticOutputParser(pydantic_object=AfterReportSummary)
            summary_system = self.prompts.get("system_messages.after_report_summary")
            summary_prompt = PromptBuilder.render(
                self.prompts.get("analysis.after_report_summary_from_events_prompt"),
                operations=operations_text,
            )
            summary_obj: AfterReportSummary = self.model_handler.run_chain(
                prompt=summary_prompt,
                parser=summary_parser,
                system_message=summary_system,
            )

            # Blocks (structured JSON -> AfterReportBlocksPlan)
            blocks_parser = PydanticOutputParser(pydantic_object=AfterReportBlocksPlan)
            blocks_system = self.prompts.get("system_messages.after_report_blocks")
            blocks_prompt = PromptBuilder.render(
                self.prompts.get("analysis.after_report_blocks_from_events_prompt"),
                operations=operations_text,
            )
            blocks_plan: AfterReportBlocksPlan = self.model_handler.run_chain(
                prompt=blocks_prompt,
                parser=blocks_parser,
                system_message=blocks_system,
            )

            blocks: list[AfterReportBlock] = []
            for block in blocks_plan.root:
                tasks = [(t, bool(performed_lookup.get(t, False))) for t in block.tasks]
                blocks.append(AfterReportBlock(name=block.name, description=block.description, tasks=tasks))

            return AfterReport(summary=summary_obj.summary, blocks=blocks)

        except Exception as e:
            logger.error("Unexpected error while generating AfterReport: %s", e)
            raise ValueError(f"Failed to process model response: {e}") from e

    @staticmethod
    def _events_to_text(events: list[OperationEvent]) -> str:
        """
        Converts a list of operation events into a formatted string representation suitable for reporting.
        
        Args:
            events: A list of operation event objects to be processed. Each event should have attributes `kind`, `target`, and optionally `data`.
        
        Returns:
            str: A newline-separated string where each line represents an event. Each line is formatted as "- <kind>: <target>" with any associated data appended as key-value pairs in parentheses. The `kind` is displayed using its `value` attribute if available, otherwise its string representation. Data items are joined with commas.
        
        Why:
            This method provides a human-readable, text-based summary of operation events, which is used in after-action reports to clearly list what operations were performed, on what targets, and with what parameters or results.
        """
        lines: list[str] = []
        for e in events:
            kind = getattr(e.kind, "value", str(e.kind))
            line = "- %s: %s" % (kind, e.target)
            data = getattr(e, "data", None) or {}
            if data:
                line += " (%s)" % ", ".join("%s=%s" % (k, v) for k, v in data.items())
            lines.append(line)
        return "\n".join(lines)

    def _operations_to_text(self, completed_tasks: list[tuple[str, bool]], task_results: dict[str, dict]) -> str:
        """
        Converts completed tasks and their results into a formatted text report.
        
        Args:
            completed_tasks: A list of tuples, each containing a task name and a boolean indicating if it was performed.
            task_results: A dictionary mapping task names to their result details, which may include 'result' and 'events'.
        
        Returns:
            str: A formatted string where each task's details are separated by a delimiter. For each task, the output includes:
                - Operation name
                - Whether it was performed ('Yes' or 'No')
                - The result (truncated to 600 characters if too long, shown as 'None' if absent)
                - A list of events (formatted via `_events_to_text`, or shown as bullet points if formatting fails)
        
        Why:
            This method generates a human-readable, structured report from operation execution data, intended for after-action summaries. It consolidates task completion status, results, and associated events into a clear, delimited text block for logging or user presentation.
        """
        parts: list[str] = []

        for name, done in completed_tasks:
            details = task_results.get(name) or {}
            result = details.get("result")
            events = details.get("events") or []

            # Result (truncate)
            result_text = "None"
            if result is not None:
                result_text = str(result)
                if len(result_text) > 600:
                    result_text = result_text[:600] + "..."

            # Events text
            try:
                events_text = self._events_to_text(events)
            except Exception:
                events_text = "\n".join("- %s" % str(e) for e in events) if events else ""

            parts.append(
                "\n".join(
                    [
                        f"Operation: {name}",
                        f"Performed: {'Yes' if done else 'No'}",
                        f"Result: {result_text}",
                        "Events:",
                        events_text or "- (none)",
                    ]
                )
            )

        return "\n\n---\n\n".join(parts)
