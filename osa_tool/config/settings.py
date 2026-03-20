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
        """
        Parse and set Git repository attributes by extracting components from the repository URL.
        
        This method is a model validator that runs after field initialization. It uses `parse_git_url` to decompose the repository URL into its constituent parts and assigns them to instance attributes. This enables easy access to the host domain, host platform, repository name, and full repository path (owner/repository) for subsequent operations within the OSA Tool.
        
        Args:
            self: The instance of the GitSettings class.
        
        Returns:
            The instance itself (self) after setting the attributes, allowing for method chaining or further validation.
        """
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
    fallback_models: list[str]
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
        """
        Sets the model API provider based on the base URL if not already set.
        
        This method acts as a Pydantic model validator that runs after field assignment.
        If the `api` attribute is not set, it automatically infers the provider from the `base_url` attribute by calling `detect_provider_from_url` and assigns the result to `api`. This ensures the provider is populated even when not explicitly configured, enabling correct API behavior downstream.
        
        Args:
            self: The ModelSettings instance.
        
        Returns:
            self: Returns the instance itself to allow for method chaining.
        """
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
    """
    Git workflow generation settings.
    """


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
        
        Loads and processes configuration from a TOML file, optionally merging and overriding values with provided command-line arguments. The processed configuration is then validated and stored as a Pydantic Settings object.
        
        Args:
            args: Parsed command-line arguments (argparse.Namespace). If provided, its values will override corresponding settings in the TOML configuration file. If None, only the TOML file is used.
        
        The initialization performs the following steps:
        1. Determines the configuration file path, checking for a custom path from args or using a default.
        2. Loads the raw TOML data from the file.
        3. If args is provided, merges the CLI argument values into the configuration data, giving CLI values precedence.
        4. Processes the configuration data to organize LLM settings into a structured format with default and task-specific sections.
        5. Validates the final processed data using the Pydantic Settings model and stores it in the instance.
        
        The method ensures the tool operates with a complete, validated configuration, combining static file settings with dynamic runtime overrides.
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
        
        This method resolves the configuration file path by first checking if a custom path
        was provided via command-line arguments. If a custom path is given and the file exists,
        that path is returned. If the custom file does not exist, a FileNotFoundError is raised.
        If no custom path is provided, the default configuration file path (generated by
        `build_config_path`) is used. If the default file does not exist, a FileNotFoundError
        is raised. This ensures the tool always operates with a valid configuration file,
        either user-specified or the project default.
        
        Args:
            self: The ConfigManager instance.
        
        Returns:
            Path to the configuration file.
        
        Raises:
            FileNotFoundError: If the specified custom config file does not exist,
                               or if the default config file does not exist.
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
        Apply CLI arguments to raw TOML configuration data.
        
        This method merges command-line argument values into the configuration dictionary, allowing CLI inputs to override or supplement the TOML file settings. This ensures that runtime options (e.g., model parameters, repository path) take precedence over static configuration.
        
        Args:
            config_data: Raw TOML configuration data loaded as a dictionary.
            args: Parsed command-line arguments (argparse.Namespace).
        
        Returns:
            dict: Updated configuration data with CLI arguments applied. The modifications occur in-place, but the dictionary is returned for convenience.
        
        The method processes three categories of CLI arguments:
        1. General LLM parameters (e.g., api, model, temperature) – these are written directly into config_data["llm"].
        2. Task-specific model overrides (e.g., model_docstring, model_readme) – these create or update nested structures under keys like "llm.for_docstring_gen".
        3. Git repository path – ensures a "git" section exists and sets the repository location.
        
        If a CLI argument is None or not present, it is ignored, preserving the existing configuration value.
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
        Process raw TOML data into a proper nested structure suitable for Pydantic validation.
        
        This method organizes configuration data by separating LLM settings into default and task-specific sections. It ensures that task-specific configurations inherit from the default settings, allowing shared parameters (like API keys or base URLs) to be defined once and overridden only where necessary for specific tasks.
        
        Args:
            config_data: Raw TOML configuration data after CLI processing.
        
        Returns:
            Processed configuration data ready for Pydantic validation. The returned dictionary includes the original 'git', 'workflows', and 'general' sections (if present), and a restructured 'llm' section. The 'llm' section is transformed into a ModelGroupSettings object containing a default ModelSettings instance and separate ModelSettings instances for each task-specific key ('for_docstring_gen', 'for_readme_gen', 'for_validation', 'for_general_tasks'), where each task inherits and can override the default settings.
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
        
        The method retrieves the appropriate LLM (Large Language Model) configuration based on the requested task. When a single-model mode is enabled (via `use_single_model`), it returns a default configuration regardless of the task type. Otherwise, it maps the task type to a specialized configuration, falling back to the default if no mapping exists.
        
        Args:
            task_type: Type of task (docstring, readme, validation, general)
        
        Returns:
            ModelSettings for the specified task type. If `use_single_model` is True, returns the default configuration. Otherwise, returns the task-specific configuration if available; otherwise returns the default.
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
        Get git settings from the configuration.
        
        This method retrieves the Git-specific configuration stored in the manager's
        loaded settings. It provides access to repository-level settings such as
        remote URLs, branch information, commit policies, and other version-control
        parameters used by the OSA Tool to analyze and enhance the repository.
        
        Returns:
            GitSettings: Git repository configuration object containing all
            Git-related settings defined in the configuration file.
        """
        return self.config.git

    def get_workflow_settings(self) -> WorkflowSettings:
        """
        Get workflow settings from the configuration.
        
        This method retrieves the workflow configuration stored in the manager's config object.
        It provides access to the settings that define the sequence and parameters of automated
        documentation and enhancement operations used by the OSA Tool pipeline.
        
        Returns:
            WorkflowSettings: The workflow configuration object containing all defined workflows.
        """
        return self.config.workflows

    def get_prompts(self) -> PromptLoader:
        """
        Get the prompt loader from the configuration.
        
        This method provides access to the prompt template loader, which is used to load
        and manage the prompt templates required by the OSA Tool's documentation generation
        and analysis pipelines. Centralizing this access ensures consistent template
        handling across different operations.
        
        Returns:
            PromptLoader: The loader instance for accessing and managing prompt templates.
        """
        return self.config.prompts
