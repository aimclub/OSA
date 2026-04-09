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
from osa_tool.utils.response_cleaner import JsonParseError
from osa_tool.utils.utils import extract_readme_content, parse_folder_name


class TextGenerator:
    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
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
        Sends a request to the model handler to generate the repository analysis.

        Returns:
            str: The generated repository analysis response from the model.
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
            return self.model_handler.send_and_parse(
                prompt=prompt,
                parser=RepositoryReport,
            )

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

        This method generates a list of strings indicating whether key files like
        README, LICENSE, documentation, examples, requirements and tests are present in the repository.

        Returns:
            list[str]: A list of strings summarizing the presence of key files in the repository.
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
    def __init__(
        self,
        config_manger: ConfigManager,
        completed_tasks: list[tuple[str, bool]],
        task_results: dict[str, dict] | None = None,
    ) -> None:
        self.config_manager = config_manger
        self.model_settings = self.config_manager.get_model_settings("general")
        self.prompts = self.config_manager.get_prompts()
        self.completed_tasks = completed_tasks
        self.task_results = task_results or {}
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)

    def make_request(self) -> AfterReport:
        """
        Sends a request to the model handler to generate the OSA work summary.

        Returns:
            The generated OSA work summary response from the model.
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
