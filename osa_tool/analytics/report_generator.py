import json
import os
from json import JSONDecodeError

import tomli as tomllib
from pydantic import ValidationError

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.prompt_builder import RepositoryReport
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmeai.config.settings import ConfigLoader
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.utils import parse_folder_name, osa_project_root


class TextGenerator:
    def __init__(self,
                 config_loader: ConfigLoader | ArticleConfigLoader,
                 sourcerank: SourceRank):
        self.config = config_loader.config
        self.sourcerank = sourcerank
        self.model_handler: ModelHandler = ModelHandlerFactory.build(
            self.config)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = os.path.join(osa_project_root(),
                                      parse_folder_name(self.repo_url))
        self.prompt_path = os.path.join(
            osa_project_root(),
            "osa_tool",
            "config",
            "standart",
            "settings",
            "prompt_for_analysis.toml"
        )

    def make_request(self) -> RepositoryReport:
        """
        Sends a request to the model handler to generate the repository analysis.

        Returns:
            str: The generated repository analysis response from the model.
        """
        response = self.model_handler.send_request(self._build_prompt())
        try:
            try:
                parsed_json = json.loads(response)
            except JSONDecodeError:
                # workaround if response starts with ```json and ends with ```
                parsed_json = json.loads(response.replace('```json', '').replace('```', ''))
            parsed_report = RepositoryReport.model_validate(parsed_json)

            return parsed_report
        except (ValidationError, json.JSONDecodeError) as e:
            raise ValueError(f"JSON parsing error: {e}")

    def _build_prompt(self) -> str:
        """
        Builds the prompt to be sent to the model for repository analysis.

        This method loads the prompt structure from a file and formats it with values
        extracted from the repository's metadata and other relevant information like
        the project name, presence of key files, and repository tree.

        Returns:
            str: The formatted prompt to be used in the model request.
        """
        with open(self.prompt_path, "rb") as f:
            prompts = tomllib.load(f)

        main_prompt = prompts.get("prompt", {}).get("main_prompt", "")
        prompt = main_prompt.format(
            project_name=self.metadata.name,
            metadata=self.metadata,
            repository_tree=self.sourcerank.tree,
            presence_files=self._extract_presence_files(),
            readme_content=self._extract_readme_content()
        )
        return prompt

    def _extract_readme_content(self) -> str | None:
        """
        Extracts the content of the README file from the repository.

        If a README file exists in the repository, it will return its content.
        It checks for both "README.md" and "README.rst" files. If no README is found,
        it returns a default message.

        Returns:
            str: The content of the README file or a message indicating absence.
        """
        if not self.sourcerank.readme_presence():
            return "No README.md file"

        for file in ["README.md", "README.rst"]:
            readme_path = os.path.join(self.base_path, file)

            if os.path.exists(readme_path):
                with open(readme_path, "r", encoding="utf-8") as f:
                    return f.read()

    def _extract_presence_files(self) -> list[str]:
        """
        Extracts information about the presence of key files in the repository.

        This method generates a list of strings indicating whether key files like
        README, LICENSE, documentation, examples, and tests are present in the repository.

        Returns:
            list[str]: A list of strings summarizing the presence of key files in the repository.
        """
        contents = [
            f"README presence is {self.sourcerank.readme_presence()}",
            f"LICENSE presence is {self.sourcerank.license_presence()}",
            f"Examples presence is {self.sourcerank.examples_presence()}",
            f"Documentation presence is {self.sourcerank.docs_presence()}",
        ]
        return contents
