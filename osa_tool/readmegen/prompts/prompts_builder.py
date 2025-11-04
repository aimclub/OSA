import os

import tomli

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.logger import logger
from osa_tool.readmegen.context.files_contents import FileContext
from osa_tool.utils import extract_readme_content, parse_folder_name, osa_project_root


class PromptBuilder:
    def __init__(self, config_loader: ConfigLoader, metadata: RepositoryMetadata):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.readme_prompt_path = os.path.join(osa_project_root(), "config", "settings", "prompts.toml")
        self.article_readme_prompt_path = os.path.join(osa_project_root(), "config", "settings", "prompts_article.toml")
        self.prompts = self.load_prompts(self.readme_prompt_path)
        self.prompts_article = self.load_prompts(self.article_readme_prompt_path)
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree

        self.repo_url = self.config.git.repository
        self.metadata = metadata
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

    def get_prompt_preanalysis(self) -> str:
        """Builds a preanalysis prompt using the repository tree and README content."""
        try:
            formatted_prompt = self.prompts["preanalysis"].format(
                repository_tree=self.tree,
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build preanalysis prompt: {e}")
            raise PromptFormatError("Could not build preanalysis prompt") from e

    def get_prompt_core_features(self, key_files: list[FileContext]) -> str:
        """Builds a core features prompt using project metadata, README content, and key files."""
        try:
            formatted_prompt = self.prompts["core_features"].format(
                project_name=self.metadata.name,
                metadata=self.metadata,
                readme_content=extract_readme_content(self.base_path),
                key_files_content=self.serialize_file_contexts(key_files),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build core features prompt: {e}")
            raise PromptFormatError("Could not build core features prompt") from e

    def get_prompt_overview(self, core_features: str) -> str:
        """Builds an overview prompt using metadata, README content, and extracted core features."""
        try:
            formatted_prompt = self.prompts["overview"].format(
                project_name=self.metadata.name,
                description=self.metadata.description,
                readme_content=extract_readme_content(self.base_path),
                core_features=core_features,
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build overview prompt: {e}")
            raise PromptFormatError("Could not build overview prompt") from e

    def get_prompt_getting_started(self, examples_files: list[FileContext]) -> str:
        """Builds a getting started prompt using metadata, README content, and example files."""
        try:
            formatted_prompt = self.prompts["getting_started"].format(
                project_name=self.metadata.name,
                readme_content=extract_readme_content(self.base_path),
                examples_files_content=self.serialize_file_contexts(examples_files),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build getting started prompt: {e}")
            raise PromptFormatError("Could not build getting started prompt") from e

    def get_prompt_files_summary(self, files_content: list[FileContext]) -> str:
        """Builds a files summary prompt using serialized file contents."""
        try:
            formatted_prompt = self.prompts_article["file_summary"].format(
                files_content=self.serialize_file_contexts(files_content),
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build files summary prompt: {e}")
            raise PromptFormatError("Could not build summary prompt") from e

    def get_prompt_pdf_summary(self, pdf_content: str) -> str:
        """Builds a PDF summary prompt using the provided PDF content."""
        try:
            formatted_prompt = self.prompts_article["pdf_summary"].format(pdf_content=pdf_content)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build PDF summary prompt: {e}")
            raise PromptFormatError("Could not build PDF summary prompt") from e

    def get_prompt_overview_article(self, files_summary: str, pdf_summary: str) -> str:
        """Builds an article overview prompt using metadata, file summary, and PDF summary."""
        try:
            formatted_prompt = self.prompts_article["overview"].format(
                project_name=self.metadata.name,
                files_summary=files_summary,
                pdf_summary=pdf_summary,
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build overview prompt: {e}")
            raise PromptFormatError("Could not build article overview prompt") from e

    def get_prompt_content_article(self, files_summary: str, pdf_summary: str) -> str:
        """Builds a content article prompt using metadata, key file content, and PDF summary."""
        try:
            formatted_prompt = self.prompts_article["content"].format(
                project_name=self.metadata.name,
                files_summary=files_summary,
                pdf_summary=pdf_summary,
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build content prompt: {e}")
            raise PromptFormatError("Could not build content prompt") from e

    def get_prompt_algorithms_article(self, key_files: list[FileContext], pdf_summary: str) -> str:
        """Builds an algorithms article prompt using metadata, file summary, and PDF summary."""
        try:
            formatted_prompt = self.prompts_article["algorithms"].format(
                project_name=self.metadata.name,
                files_content=key_files,
                pdf_summary=pdf_summary,
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build algorithms prompt: {e}")
            raise PromptFormatError("Could not build algorithms prompt") from e

    def get_prompt_translate_readme(self, readme_content: str, target_language: str) -> str:
        """Builds a prompt to translate README into target language"""
        try:
            formatted_prompt = self.prompts["translate"].format(
                target_language=target_language,
                readme_content=readme_content,
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build readme translation prompt: {e}")
            raise PromptFormatError("Could not build translation prompt") from e

    def get_prompt_detect_citation(self) -> str:
        """Builds a detection of citation prompt."""
        try:
            formatted_prompt = self.prompts["citation"].format(readme=extract_readme_content(self.base_path))
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build detection of citation prompt: {e}")
            raise PromptFormatError("Could not build detection of citation prompt") from e

    def get_prompt_refine_readme_step1(self, generated_readme: str) -> str:
        """Builds a prompt to merge original README details into the generated structure."""
        try:
            formatted_prompt = self.prompts["refine_step1"].format(
                old_readme=extract_readme_content(self.base_path), new_readme=generated_readme
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build refine readme step 1 prompt: {e}")
            raise PromptFormatError("Could not build refine readme step 1 prompt") from e

    def get_prompt_refine_readme_step2(self, readme: str) -> str:
        """Builds a prompt to clean duplicates and normalize formatting in README."""
        try:
            formatted_prompt = self.prompts["refine_step2"].format(readme=readme)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build refine readme step 2 prompt: {e}")
            raise PromptFormatError("Could not build refine readme step 2 prompt") from e

    def get_prompt_refine_readme_step3(self, readme: str) -> str:
        """Builds a prompt to finalize README headings, ToC, and formatting consistency."""
        try:
            formatted_prompt = self.prompts["refine_step3"].format(readme=readme)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build refine readme step 3 prompt: {e}")
            raise PromptFormatError("Could not build refine readme step 3 prompt") from e

    def get_prompt_clean_readme_step1(self, readme: str) -> str:
        """Builds a prompt to remove duplicate commands, text, and media from README."""
        try:
            formatted_prompt = self.prompts["clean_step1"].format(readme=readme)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build cleaning readme step 1 prompt: {e}")
            raise PromptFormatError("Could not build cleaning readme step 1 prompt") from e

    def get_prompt_clean_readme_step2(self, readme: str) -> str:
        """Builds a prompt to delete semantically duplicated content across README sections."""
        try:
            formatted_prompt = self.prompts["clean_step2"].format(readme=readme)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build cleaning readme step 2 prompt: {e}")
            raise PromptFormatError("Could not build cleaning readme step 2 prompt") from e

    def get_prompt_clean_readme_step3(self, readme: str) -> str:
        """Builds a prompt to finalize README formatting and ensure GFM compliance."""
        try:
            formatted_prompt = self.prompts["clean_step3"].format(readme=readme)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build cleaning readme step 3 prompt: {e}")
            raise PromptFormatError("Could not build cleaning readme step 3 prompt") from e

    def get_prompt_article_name_extraction(self, pdf_content: str) -> str:
        """Builds an article name extraction prompt"""
        try:
            formatted_prompt = self.prompts_article["article_name_extraction"].format(pdf_content=pdf_content)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build article name extraction prompt: {e}")
            raise PromptFormatError("Could not build article name extraction prompt") from e

    @staticmethod
    def serialize_file_contexts(files: list[FileContext]) -> str:
        """
        Serializes a list of FileContext objects into a string.

        Args:
            files (list[FileContext]): A list of FileContext objects representing files.

        Returns:
            str: A string representing the serialized file data.
                Each section includes the file's name, path, and content.
        """
        return "\n\n".join(f"### {f.name} ({f.path})\n{f.content}" for f in files)

    @staticmethod
    def load_prompts(path: str, section: str = "prompts") -> dict:
        """
        Load prompts from a TOML file and return the specified section as a dictionary.

        Args:
            path (str): Path to the TOML file.
            section (str): Section inside the TOML to extract (default: "prompts").

        Returns:
            dict: Dictionary with prompts from the specified section.
        """
        try:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Prompts file {path} not found.")

            with open(path, "rb") as f:
                toml_data = tomli.load(f)

            if section not in toml_data:
                raise KeyError(f"Section '{section}' not found in {path}.")

            return toml_data[section]
        except Exception as e:
            logger.error(f"Failed to load prompts from {path}: {e}")
            raise PromptLoadError(f"Could not load prompts from {path}") from e


class PromptBuilderError(Exception):
    """Base exception for PromptBuilder errors."""


class PromptLoadError(PromptBuilderError):
    """Raised when loading prompts from a file fails."""


class PromptFormatError(PromptBuilderError):
    """Raised when building a specific prompt fails."""
