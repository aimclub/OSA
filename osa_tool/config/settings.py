"""Pydantic models and settings for the osa_tool package."""

from __future__ import annotations

import os.path
from pathlib import Path
from typing import Any, List, Literal

import tomli
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    NonNegativeFloat,
    PositiveInt,
    model_validator,
)

from osa_tool.utils.utils import build_config_path, parse_git_url


class GitSettings(BaseModel):
    """
    User repository settings for a remote codebase.
    """

    repository: Path | str
    full_name: str | None = None
    host_domain: str | None = None
    host: str | None = None
    name: str = ""

    @model_validator(mode="after")
    def set_git_attributes(self):
        """Parse and set Git repository attributes."""
        self.host_domain, self.host, self.name, self.full_name = parse_git_url(str(self.repository))
        return self


class ModelSettings(BaseModel):
    """
    LLM API model settings and parameters.
    """

    api: str
    rate_limit: PositiveInt
    base_url: str
    encoder: str
    host_name: AnyHttpUrl
    localhost: AnyHttpUrl
    model: str
    path: str
    temperature: NonNegativeFloat
    max_tokens: PositiveInt
    context_window: PositiveInt
    top_p: NonNegativeFloat
    max_retries: PositiveInt


class WorkflowSettings(BaseModel):
    """Git workflow generation settings."""

    generate_workflows: bool = Field(
        default=False,
        description="Flag indicating whether to generate workflows.",
    )
    include_tests: bool = Field(default=True, description="Include unit tests workflow.")
    include_black: bool = Field(default=True, description="Include Black formatter workflow.")
    include_pep8: bool = Field(default=True, description="Include PEP 8 compliance workflow.")
    include_autopep8: bool = Field(default=False, description="Include autopep8 formatter workflow.")
    include_fix_pep8: bool = Field(default=False, description="Include fix-pep8 command workflow.")
    include_pypi: bool = Field(default=False, description="Include PyPI publish workflow.")
    python_versions: List[str] = Field(
        default_factory=lambda: ["3.9", "3.10"],
        description="Python versions for workflows.",
    )
    pep8_tool: Literal["flake8", "pylint"] = Field(default="flake8", description="Tool for PEP 8 checking.")
    use_poetry: bool = Field(default=False, description="Use Poetry for packaging in PyPI workflow.")
    branches: List[str] = Field(
        default_factory=lambda: ["main", "master"],
        description="Branches to trigger workflows on.",
    )
    codecov_token: bool = Field(default=False, description="Use Codecov token for coverage upload.")
    include_codecov: bool = Field(
        default=True,
        description="Include Codecov coverage step in a unit tests workflow.",
    )


class Settings(BaseModel):
    """
    Pydantic settings model for the readmegen package.
    """

    git: GitSettings
    llm: ModelSettings
    workflows: WorkflowSettings

    model_config = ConfigDict(
        validate_assignment=True,
    )


class ConfigLoader:
    """
    Loads the configuration settings for the readmegen package.
    """

    def __init__(self) -> None:
        """Initialize ConfigLoader with the base configuration file."""
        self._load_config()

    def _load_config(self) -> Settings:
        """Loads the base configuration file."""
        file_path_config = self._get_config_path()

        config_dict = self._read_config(file_path_config)

        self.config = Settings.model_validate(config_dict)
        return self.config

    @staticmethod
    def _get_config_path() -> str:
        """
        Helper method to get the correct resource path,
        looking outside the package.
        """
        file_path = build_config_path()
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Configuration file {file_path} not found.")
        return str(file_path)

    @staticmethod
    def _read_config(path: str) -> dict[str, Any]:
        with open(path, "rb") as file:
            data = tomli.load(file)

        return {key.lower(): value for key, value in data.items()}
