"""Pydantic models and settings for the osa_tool package."""

from __future__ import annotations

import os.path
from pathlib import Path
from typing import Any

import tomli
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    model_validator,
    NonNegativeFloat,
    PositiveInt
)

from osa_tool.utils import osa_project_root, parse_git_url


class GitSettings(BaseModel):
    """
    User repository settings for a remote codebase.
    """

    repository: Path | str
    full_name: str | None = None
    host_domain: str | None = None
    host: str | None = None
    name: str = ""

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def set_git_attributes(self):
        """Parse and set Git repository attributes."""
        self.host_domain, self.host, self.name, self.full_name = parse_git_url(
            str(self.repository)
        )
        return self


class ModelSettings(BaseModel):
    """
    LLM API model settings and parameters.
    """

    api: str
    url: str
    context_window: PositiveInt
    encoder: str
    host_name: AnyHttpUrl
    localhost: AnyHttpUrl
    model: str
    path: str
    temperature: NonNegativeFloat
    tokens: PositiveInt
    top_p: NonNegativeFloat


class Settings(BaseModel):
    """
    Pydantic settings model for the readmegen package.
    """

    git: GitSettings
    llm: ModelSettings

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
        file_path = os.path.join(
            osa_project_root(),
            "config",
            "settings",
            "config.toml"
        )
        if not os.path.exists(file_path):
            raise FileNotFoundError(
                f"Configuration file {file_path} not found.")
        return str(file_path)

    @staticmethod
    def _read_config(path: str) -> dict[str, Any]:
        with open(path, "rb") as file:
            data = tomli.load(file)

        return {key.lower(): value for key, value in data.items()}
