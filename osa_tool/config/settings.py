"""Pydantic models and settings for the osa_tool package."""

from __future__ import annotations

import os.path
from argparse import Namespace
from datetime import datetime
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
    field_validator,
    model_validator,
)

from osa_tool.core.git.request_utils import RetryConfig
from osa_tool.utils.prompts_builder import PromptLoader
from osa_tool.utils.utils import (
    build_config_path,
    detect_provider_from_url,
    parse_date_argument,
    parse_git_url,
    is_path,
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
    osa_branch_name: str = "osa_tool"
    based_on_date: datetime | None = None
    retry: RetryConfig = Field(default_factory=RetryConfig)

    @field_validator("based_on_date", mode="before")
    @classmethod
    def normalize_based_on_date(cls, value: Any) -> datetime | None:
        """Accept CLI strings and native TOML dates, storing them as an aware datetime."""
        if value is None or value == "":
            return None
        return parse_date_argument(value)

    @model_validator(mode="after")
    def set_git_attributes(self):
        """Parse and set Git repository attributes."""
        if is_path(self.repository):
            if os.path.isdir(self.repository):
                basename = os.path.basename(self.repository)
                self.name = basename
                self.full_name = f"local/{basename}"
            else:
                raise ValueError(f"{self.repository} does not exist.")
        else:
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
    for_general_tasks: ModelSettings | None = None
    for_repository_quality: ModelSettings | None = None
    for_paper_claims: ModelSettings | None = None
    for_paper_verification: ModelSettings | None = None


class PaperMarkerSettings(BaseModel):
    """Marker conversion settings used by the typed paper-claims stage."""

    extract_images: bool = False
    cache_root: Path | None = None
    force_refresh: bool = False
    low_vram: bool = True
    process_isolation: bool = True
    log_cuda_memory: bool = True
    marker_config: dict[str, Any] = Field(default_factory=dict)


class PaperClaimsSettings(BaseModel):
    """Stable execution settings for PDF-to-typed-claims extraction."""

    pages_per_chunk: PositiveInt = 5
    max_retries: PositiveInt = 5
    dedup_batch_size: int = Field(default=50, ge=2)
    marker: PaperMarkerSettings = Field(default_factory=PaperMarkerSettings)

    def to_pipeline_options(self):
        """Build paper-claims options without making config depend on its implementation at import time."""
        from osa_tool.operations.analysis.paper_claims.models import MarkerOptions, PipelineOptions

        return PipelineOptions(
            pages_per_chunk=self.pages_per_chunk,
            max_retries=self.max_retries,
            dedup_batch_size=self.dedup_batch_size,
            marker=MarkerOptions(**self.marker.model_dump()),
        )


class PaperVerificationSettings(BaseModel):
    """Bounded repository-context and claim-verification execution settings."""

    batch_size: int = Field(default=25, ge=1, le=50)
    candidate_file_limit: PositiveInt = 6
    source_snippet_max_lines: PositiveInt = 250
    repository_tree_max_paths: PositiveInt = 300
    csv_file_limit: PositiveInt = 5


class PaperAnalysisSettings(BaseModel):
    """Policy and execution settings for the composed paper-analysis operation."""

    output_dir: Path = Path("paper_analysis")
    include_repository_quality: bool = False
    only_high_medium_verifiability: bool = True
    hide_low_confidence: bool = True
    paper_claims: PaperClaimsSettings = Field(default_factory=PaperClaimsSettings)
    verification: PaperVerificationSettings = Field(default_factory=PaperVerificationSettings)


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
    paper_analysis: PaperAnalysisSettings = Field(default_factory=PaperAnalysisSettings)
    prompts: PromptLoader = Field(default_factory=PromptLoader)

    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


class ConfigManager:
    """
    Manages configuration loading and provides model settings for different tasks.
    """

    TASK_MODEL_MAP = {
        "docstring": "for_docstring_gen",
        "readme": "for_readme_gen",
        "general": "for_general_tasks",
        "repository_quality": "for_repository_quality",
        "paper_claims": "for_paper_claims",
        "paper_verification": "for_paper_verification",
    }

    def __init__(self, args: Namespace | None = None):
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

        from osa_tool.core.git import request_utils

        request_utils.DEFAULT_RETRY_CONFIG = request_utils.RetryConfig(**self.config.git.retry.model_dump())

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
    def _apply_cli_args_to_config_data(config_data: dict, args: Namespace) -> dict:
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
            "for_general_tasks": "model_general",
            "for_repository_quality": "model_repository_quality",
            "for_paper_claims": "model_paper_claims",
            "for_paper_verification": "model_paper_verification",
        }

        for task_type, arg_name in task_models.items():
            if hasattr(args, arg_name) and getattr(args, arg_name):
                if "llm" not in config_data:
                    config_data["llm"] = {}
                if task_type not in config_data["llm"]:
                    config_data["llm"][task_type] = {}
                config_data["llm"][task_type]["model"] = getattr(args, arg_name)

        if "git" not in config_data:
            config_data["git"] = {}
        config_data["git"]["repository"] = args.repository

        if getattr(args, "based_on_date", None):
            config_data["git"]["based_on_date"] = args.based_on_date

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
            if "for_validation" in llm_data:
                raise ValueError(
                    "[llm.for_validation] was removed. Configure [llm.for_repository_quality], "
                    "[llm.for_paper_claims], or [llm.for_paper_verification] instead."
                )
            if "for_thesis_verification" in llm_data:
                raise ValueError("[llm.for_thesis_verification] was removed. Use [llm.for_paper_verification] instead.")

            default_settings = {}
            task_sections = {}

            for key, value in llm_data.items():
                if key in [
                    "for_docstring_gen",
                    "for_readme_gen",
                    "for_general_tasks",
                    "for_repository_quality",
                    "for_paper_claims",
                    "for_paper_verification",
                ]:
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

        if "thesis_analysis" in config_data:
            raise ValueError("[thesis_analysis] was removed. Use [paper_analysis] instead.")

        if "paper_analysis" in config_data:
            processed["paper_analysis"] = config_data["paper_analysis"]

        return processed

    def get_model_settings(self, task_type: str) -> ModelSettings:
        """
        Get model settings for specific task type.

        Args:
            task_type: Type of task (docstring, readme, general, repository_quality,
                paper_claims, paper_verification)

        Returns:
            ModelSettings for the specified task type
        """
        use_single_model = getattr(self.args, "use_single_model", False) if self.args else False

        if use_single_model:
            return self.config.llm.default

        task_attr = self.TASK_MODEL_MAP.get(task_type)
        task_config = getattr(self.config.llm, task_attr) if task_attr else None

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

    def get_paper_analysis_settings(self) -> PaperAnalysisSettings:
        """Return typed policy and execution settings for paper analysis."""
        return self.config.paper_analysis

    def get_prompts(self) -> PromptLoader:
        """
        Get prompt loader.

        Returns:
            PromptLoader: Loader for prompt templates
        """
        return self.config.prompts
