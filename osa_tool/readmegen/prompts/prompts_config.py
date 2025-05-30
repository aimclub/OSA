import os

import tomli
from pydantic import BaseModel, Field

from osa_tool.utils import osa_project_root


class PromptConfig(BaseModel):
    """
    Model for validating the structure of prompts loaded from prompts.toml.
    """

    preanalysis: str = Field(
        ...,
        description="Template for highlighting key files based on structure and README.",
    )
    core_features: str = Field(
        ..., description="Template for extracting core features of the project."
    )
    overview: str = Field(
        ..., description="Template for generating a concise project overview."
    )
    getting_started: str = Field(
        ..., description="Template for generating a Getting Started section"
    )


class PromptLoader:
    def __init__(self):
        self.prompts = self.load_prompts()

    def load_prompts(self) -> PromptConfig:
        """
        Load and validate prompts from prompts.toml file.
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
            osa_project_root(), "config", "settings", "prompts.toml"
        )
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompts file {file_path} not found.")
        return str(file_path)
