"""Pydantic models and settings for the osa_tool package."""

from __future__ import annotations

import os.path
from pathlib import Path
from typing import List, Literal

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

from osa_tool.utils.prompts_builder import PromptLoader
from osa_tool.utils.utils import (
    build_config_path,
    detect_provider_from_url,
    parse_git_url,
)


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

    api: str | None = None
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
    allowed_providers: list[str]
    system_prompt: str

    model_config = ConfigDict(extra="allow")

    @model_validator(mode="after")
    def set_model_api(self):
        if not self.api:
            self.api = detect_provider_from_url(self.base_url)
        return self


class ModelGroupSettings(BaseModel):
    """
    LLM model settings grouped by task type.
    """

    default: ModelSettings
    for_docstring_gen: ModelSettings | None = None
    for_readme_gen: ModelSettings | None = None
    for_validation: ModelSettings | None = None
    for_general_tasks: ModelSettings | None = None


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
    Pydantic settings model.
    """

    git: GitSettings
    llm: ModelGroupSettings
    workflows: WorkflowSettings
    prompts: PromptLoader = Field(default_factory=PromptLoader)

    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


class ConfigManager:
    """
    Manages configuration loading and provides model settings for different tasks.
    """

    def __init__(self, args=None):
        """
        Initialize ConfigManager with CLI arguments.

        Args:
            args: Command-line arguments (argparse.Namespace)
        """
        self.args = args

        config_path = self._get_config_path()

        with open(config_path, "rb") as file:
            config_data = tomli.load(file)

        if args:
            config_data = self._apply_cli_args_to_config_data(config_data, args)

        processed_data = self._process_config_data(config_data)

        self.config = Settings.model_validate(processed_data)

    def _get_config_path(self) -> str:
        """
        Determine config file path from args or use default.

        Returns:
            str: Path to configuration file

        Raises:
            FileNotFoundError: If specified config file doesn't exist
        """
        if self.args and hasattr(self.args, "config_file") and self.args.config_file:
            config_path = self.args.config_file
            if os.path.exists(config_path):
                return config_path
            else:
                raise FileNotFoundError(f"Custom configuration file not found: {config_path}")

        config_path = build_config_path()
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Default configuration file not found: {config_path}")

        return config_path

    @staticmethod
    def _apply_cli_args_to_config_data(config_data: dict, args) -> dict:
        """
        Apply CLI arguments to raw config data.

        Args:
            config_data: dict - Raw TOML configuration data
            args: Command-line arguments (argparse.Namespace)

        Returns:
            dict: Updated configuration data with CLI arguments applied
        """
        model_params = [
            "api",
            "base_url",
            "model",
            "temperature",
            "max_tokens",
            "context_window",
            "top_p",
            "max_retries",
        ]

        for param in model_params:
            if hasattr(args, param) and getattr(args, param) is not None:
                config_data["llm"][param] = getattr(args, param)

        task_models = {
            "for_docstring_gen": "model_docstring",
            "for_readme_gen": "model_readme",
            "for_validation": "model_validation",
            "for_general_tasks": "model_general",
        }

        for task_type, arg_name in task_models.items():
            if hasattr(args, arg_name) and getattr(args, arg_name):
                task_key = f"llm.{task_type}"
                if task_key not in config_data:
                    config_data[task_key] = {}
                config_data[task_key]["model"] = getattr(args, arg_name)

        if "git" not in config_data:
            config_data["git"] = {}
        config_data["git"]["repository"] = args.repository

        return config_data

    @staticmethod
    def _process_config_data(config_data: dict) -> dict:
        """
        Process raw TOML data into proper nested structure.

        Args:
            config_data: dict - Raw TOML configuration data after CLI processing

        Returns:
            dict: Processed configuration data ready for Pydantic validation
        """
        processed = {}

        if "git" in config_data:
            processed["git"] = config_data["git"]

        if "llm" in config_data:
            llm_data = config_data["llm"]

            default_settings = {}
            task_sections = {}

            for key, value in llm_data.items():
                if key in ["for_docstring_gen", "for_readme_gen", "for_validation", "for_general_tasks"]:
                    task_sections[key] = value
                else:
                    default_settings[key] = value

            default_model = ModelSettings(**default_settings)

            task_settings = {}
            for task_name, task_config in task_sections.items():
                task_data = default_settings.copy()
                task_data.update(task_config)
                task_settings[task_name] = ModelSettings(**task_data)

            processed["llm"] = ModelGroupSettings(default=default_model, **task_settings).model_dump()

        if "workflows" in config_data:
            processed["workflows"] = config_data["workflows"]

        if "general" in config_data:
            processed["general"] = config_data["general"]

        return processed

    def get_model_settings(self, task_type: str) -> ModelSettings:
        """
        Get model settings for specific task type.

        Args:
            task_type: Type of task (docstring, readme, validation, general)

        Returns:
            ModelSettings for the specified task type
        """
        use_single_model = getattr(self.args, "use_single_model", True) if self.args else True

        if use_single_model:
            return self.config.llm.default

        task_config_map = {
            "docstring": self.config.llm.for_docstring_gen,
            "readme": self.config.llm.for_readme_gen,
            "validation": self.config.llm.for_validation,
            "general": self.config.llm.for_general_tasks,
        }

        task_config = task_config_map.get(task_type)

        return task_config if task_config else self.config.llm.default

    def get_git_settings(self) -> GitSettings:
        """
        Get git settings.

        Returns:
            GitSettings: Git repository configuration
        """
        return self.config.git

    def get_workflow_settings(self) -> WorkflowSettings:
        """
        Get workflow settings.

        Returns:
            WorkflowSettings: Workflow configuration
        """
        return self.config.workflows

    def get_prompts(self) -> PromptLoader:
        """
        Get prompt loader.

        Returns:
            PromptLoader: Loader for prompt templates
        """
        return self.config.prompts
