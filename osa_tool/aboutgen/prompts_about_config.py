import os

import tomli
from pydantic import BaseModel, Field

from osa_tool.utils import osa_project_root


class PromptConfig(BaseModel):
    """Model for validating the structure of prompts loaded from prompts_about_section.toml."""
    description: str = Field(...,
                             description="Template for generating a project description.")
    topics: str = Field(...,
                        description="Template for generating project topics.")
    analyze_urls: str = Field(...,
                              description="Template for analyzing project urls.")


class PromptAboutLoader:
    def __init__(self):
        self.prompts = self.load_prompts()

    def load_prompts(self) -> PromptConfig:
        """
        Load and validate prompts from prompts_about_section.toml file.
        """
        with open(self._get_prompts_path(), "rb") as file:
            prompts = tomli.load(file)

        return PromptConfig(**prompts.get("prompts", {}))

    @staticmethod
    def _get_prompts_path() -> str:
        """
        Helper method to get the correct resource path,
        looking outside the package.
        """
        file_path = os.path.join(
            osa_project_root(),
            "config",
            "settings",
            "prompts_about_section.toml"
        )
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Prompts file {file_path} not found.")
        return str(file_path)
