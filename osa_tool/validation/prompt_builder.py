import os

import tomli

from osa_tool.logger import logger
from osa_tool.utils import osa_project_root


class PromptBuilderError(Exception):
    """Base exception for PromptBuilder errors."""


class PromptLoadError(PromptBuilderError):
    """Raised when loading prompts from a file fails."""


class PromptFormatError(PromptBuilderError):
    """Raised when building a specific prompt fails."""


class PromptBuilder:
    def __init__(self):
        self.prompts_path = os.path.join(osa_project_root(), "config", "settings", "prompts_validation.toml")
        self.prompts = self.load_prompts(self.prompts_path)

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

    def get_prompt_to_analyze_code_file(self, file_content: str) -> str:
        """Builds a prompt to analyze source code file."""
        try:
            formatted_prompt = self.prompts["analyze_code_file"].format(file_content=file_content)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build code analyzing prompt: {e}")
            raise PromptFormatError("Could not build code analyzing prompt") from e

    def get_prompt_to_extract_sections_from_doc(self, doc_content: str) -> str:
        """Builds a prompt to extract sections from a document."""
        try:
            formatted_prompt = self.prompts["extract_document_sections"].format(doc_content=doc_content)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build document extraction prompt: {e}")
            raise PromptFormatError("Could not build document extraction prompt") from e

    def get_prompt_to_validate_doc_against_repo(self, doc_info: str, code_files_info: str) -> str:
        """Builds a prompt to validate document against repo."""
        try:
            formatted_prompt = self.prompts["validate_doc_against_repo"].format(
                doc_info=doc_info, code_files_info=code_files_info
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build document validation prompt: {e}")
            raise PromptFormatError("Could not build document validation prompt") from e

    def get_prompt_to_extract_sections_from_paper(self, paper_content: str) -> str:
        """Builds a prompt to extract sections from a paper."""
        try:
            formatted_prompt = self.prompts["extract_paper_section"].format(paper_content=paper_content)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build paper extraction prompt: {e}")
            raise PromptFormatError("Could not build paper extraction prompt") from e

    def get_prompt_to_validate_paper_against_repo(self, paper_info: str, code_files_info: str) -> str:
        """Builds a prompt to validate paper against repo."""
        try:
            formatted_prompt = self.prompts["validate_paper_against_repo"].format(
                paper_info=paper_info, code_files_info=code_files_info
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build paper validation prompt: {e}")
            raise PromptFormatError("Could not build paper validation prompt") from e
