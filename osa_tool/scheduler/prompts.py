import os
from typing import Optional

import tomli
from pydantic import BaseModel, Field

from osa_tool.utils import osa_project_root


class PromptConfig(BaseModel):
    """
    Model for validating the structure of prompts loaded from prompt_for_scheduler.toml.
    """

    report: bool = Field(
        False,
        description="Generate an additional report describing the analyzed repository for user reference. Does not affect the repository itself.",
    )
    translate_dirs: bool = Field(
        False, description="Translate directory and file names to English if they are not already in English."
    )
    docstring: bool = Field(False, description="Generate docstrings for functions and classes if .py files is present.")
    ensure_license: Optional[str] = Field(
        None,
        description="Generate a license file for the repository if missing. Set to 'bsd-3', 'mit', or 'ap2' to enable. If None, no license is added.",
    )
    community_docs: bool = Field(
        False,
        description="Generate community-related files such as CODE_OF_CONDUCT.md, PULL_REQUEST_TEMPLATE.md, and other supporting documentation.",
    )
    readme: bool = Field(
        False,
        description="Generate a README file for the repository if it is missing or of insufficient quality. If a clear and well-structured README is detected, this should be set to False.",
    )
    organize: bool = Field(
        False,
        description="Organize the repository by adding 'tests' and 'examples' directories if they do not already exist.",
    )
    about: bool = Field(False, description="Generate About section for the repository if it is missing.")

    class Config:
        extra = "ignore"


class PromptLoader:
    def __init__(self):
        self.prompts = self.load_prompts()

    def load_prompts(self) -> dict:
        """
        Load and validate prompts from prompts.toml file.
        """
        with open(self._get_prompts_path(), "rb") as file:
            prompts = tomli.load(file)

        return prompts.get("prompts", {})

    @staticmethod
    def _get_prompts_path() -> str:
        """
        Helper method to get the correct resource path.
        """
        file_path = os.path.join(osa_project_root(), "config", "settings", "prompt_for_scheduler.toml")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Prompts file {file_path} not found.")
        return str(file_path)
