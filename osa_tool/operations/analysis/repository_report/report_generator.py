import os

from pydantic import ValidationError

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.operations.analysis.repository_report.response_validation import (
    RepositoryReport,
    RepositoryStructure,
    ReadmeEvaluation,
    CodeDocumentation,
    OverallAssessment,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor, JsonParseError
from osa_tool.utils.utils import extract_readme_content, parse_folder_name


class TextGenerator:
    def __init__(self, config_loader: ConfigLoader, metadata: RepositoryMetadata):
        self.config = config_loader.config
        self.sourcerank = SourceRank(config_loader)
        self.prompts = self.config.prompts
        self.metadata = metadata
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
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
