"""Pydantic models and settings for the readmegen package."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    FilePath,
    NonNegativeFloat,
    PositiveInt,
    field_validator,
    model_validator,
)
from pydantic_extra_types.color import Color

from readmegen.config.constants import (
    BadgeStyleOptions,
    HeaderStyleOptions,
    ImageOptions,
)
from readmegen.errors import GitValidationError
from readmegen.logger import get_logger
from readmegen.readers.git.providers import GitURL, parse_git_url
from readmegen.utils.file_handler import FileHandler
from readmegen.utils.file_resource import get_resource_path

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

_logger = get_logger(__name__)


class APISettings(BaseModel):
    """
    LLM API settings and parameters.
    """

    rate_limit: PositiveInt = Field(gt=0, le=25, description="API rate limit.")
    system_message: str = Field(description="LLM system prompt content field.")


class FileSettings(BaseModel):
    """
    File path resources for the readmegen package.
    """

    docs_list: str = Field(description="List of files to use in README file")
    ignore_list: str = Field(description="List of files to ignore.")
    languages: str = Field(description="Extension to language mappings.")
    parsers: str = Field(description="Common dependency file names.")
    prompts: str = Field(description="LLM API prompt templates.")
    tool_config: str = Field(description="Development tool configurations.")
    tooling: str = Field(description="Development tools and utilities.")
    shieldsio_icons: str = Field(description="Shields.io svg icon badges.")
    skill_icons: str = Field(description="Skill icon badges.")


class GitSettings(BaseModel):
    """
    User repository settings for a remote or local codebase.
    """

    repository: Path | str
    full_name: str | None = None
    host_domain: str | None = None
    host: str | None = None
    name: str = ""

    model_config = ConfigDict(extra="forbid")

    @field_validator("repository")
    def validate_repository(cls, value: Path | str) -> Path | str:
        """Validates the repository path or Git URL."""
        if isinstance(value, Path) or (
            isinstance(value, str)
            and Path(value).is_dir()
            and Path(value).exists()
        ):
            return value
        try:
            return str(GitURL.create(value).url)
        except ValueError as exc:
            raise GitValidationError(
                f"Invalid Git repository URL or path: {value}",
            ) from exc

    @model_validator(mode="after")
    def set_git_attributes(self):
        """Parse and set Git repository attributes."""
        self.host_domain, self.host, self.name, self.full_name = parse_git_url(
            str(self.repository)
        )
        return self


class MarkdownSettings(BaseModel):
    """
    Markdown code template blocks for building the README.md file.
    """

    align: Literal["left", "center", "right"] = Field(
        default="center", description="align for markdown content."
    )
    badge_color: Color = Field(
        default_factory=lambda: Color("blue"),
        description="Badge color (https://www.w3.org/TR/SVG11/types."
        "html#ColorKeywords)",
    )
    badge_style: BadgeStyleOptions = Field(
        default=BadgeStyleOptions.DEFAULT, description="Badge icon style type."
    )
    badges_tech_stack: str
    badges_tech_stack_text: str
    core_features: str = Field(
        default="INSERT-PROJECT-FEATURES", description="Project core features."
    )
    header_style: str = Field(
        default=HeaderStyleOptions.CLASSIC,
        description="Header style for the project README.",
    )
    image: AnyHttpUrl | FilePath = Field(
        default=ImageOptions.ITMO_LOGO,
        description="Project image URL or file path",
    )
    image_width: str = Field(default="100%")
    overview: str = Field(default="INSERT-PROJECT-OVERVIEW")
    placeholder: str = Field(default="<code>❯ REPLACE-ME</code>")
    examples: str
    shieldsio_icons: str
    skill_icons: str
    table_of_contents: str
    license: str
    documentation: str
    contacts: str
    acknowledgments: str

    model_config = ConfigDict(
        use_enum_values=True, arbitrary_types_allowed=True
    )

    @field_validator("badge_color")
    def set_color(cls, value: str) -> str:
        """Field validator to set the badge color."""
        try:
            return Color(value).as_hex(format="long").lstrip("#")
        except ValueError:
            _logger.error(f"Invalid color provided: {value}", exc_info=True)
            return cls.model_fields["badge_color"].default


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

    api: APISettings
    files: FileSettings
    git: GitSettings
    llm: ModelSettings
    md: MarkdownSettings

    model_config = ConfigDict(
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def generate_banner(self) -> Self:
        """Generates the project banner based on the settings."""
        header_style = self.md.header_style.lower()

        if header_style == HeaderStyleOptions.CLASSIC.value:
            self.md.header_style = HeaderStyleOptions.CLASSIC
            self.md.image_width = "70%"

        return self


class ConfigLoader:
    """
    Loads the configuration settings for the readme-ai package.
    """

    file_handler: FileHandler = FileHandler()
    config_file: str = "settings/config.toml"
    template_file: str = "templates/ITMO_template.toml"

    def __init__(self, config_dir: str) -> None:
        """Initialize ConfigLoader with the base configuration file."""
        self.config_dir = Path(config_dir).resolve()
        self._load_config()
        self._load_settings()

    def _load_config(self) -> Settings:
        """Loads the base configuration file."""
        file_path_config = self._get_config_path(self.config_file)
        file_path_template = self._get_config_path(self.template_file)

        config_dict = self.file_handler.read(file_path_config)
        template_dict = self.file_handler.read(file_path_template)
        config_dict.update(template_dict)

        self.config = Settings.model_validate(config_dict)
        return self.config

    def _load_settings(self) -> dict[str, dict]:
        """Loads all TOML config files from ./config/settings/*.toml."""
        settings = self.config.model_dump()

        for key, file_path in settings["files"].items():
            if file_path.endswith(".toml"):
                file_path = self._get_config_path("settings/" + file_path)
                config_dict = self.file_handler.read(file_path)
                settings[key] = config_dict
                setattr(self, key, config_dict)
                _logger.info(f"Configuration file loaded: {file_path}")

        return settings

    def _get_config_path(self, file_path: str) -> str:
        """
        Helper method to get the correct resource path,
        looking outside the package.
        """
        file_path = Path(self.config_dir) / file_path
        if not file_path.exists():
            raise FileNotFoundError(
                f"Configuration file {file_path} not found.")
        return str(file_path)
