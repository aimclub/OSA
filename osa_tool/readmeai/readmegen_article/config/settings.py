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
    model_validator,
)

from osa_tool.readmeai.config.constants import (
    HeaderStyleOptions,
    ImageOptions,
)

from osa_tool.readmeai.logger import get_logger
from osa_tool.readmeai.utils.file_handler import FileHandler
from osa_tool.readmeai.utils.file_resource import get_resource_path

from osa_tool.readmeai.config.settings import APISettings, FileSettings, GitSettings, ModelSettings

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self

_logger = get_logger(__name__)


class ArticleMarkdownSettings(BaseModel):
    """
    Markdown code template blocks for building the README.md file.
    """

    align: Literal["left", "center", "right"] = Field(
        default="center", description="align for markdown content."
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
    content: str = Field(default="INSERT-PROJECT-CONTENTS")
    algorithms: str = Field(default="INSERT-USED-ALGORITHMS")
    placeholder: str = Field(default="<code>❯ REPLACE-ME</code>")
    

    model_config = ConfigDict(
        use_enum_values=True, arbitrary_types_allowed=True
    )


class ArticleSettings(BaseModel):
    """
    Pydantic settings model for the readmegen package.
    """

    api: APISettings
    files: FileSettings
    git: GitSettings
    llm: ModelSettings
    md: ArticleMarkdownSettings

    model_config = ConfigDict(
        validate_assignment=True,
    )

    @model_validator(mode="after")
    def generate_banner(self) -> Self:
        """Generates the project banner based on the settings."""
        header_style = self.md.header_style.lower()

        if header_style == HeaderStyleOptions.CLASSIC.value:
            self.md.header_style = HeaderStyleOptions.CLASSIC
            self.md.image_width = "20%"

        return self


class ArticleConfigLoader:
    """
    Loads the configuration settings for the readmeai package.
    """

    file_handler: FileHandler = FileHandler()
    config_file: str = "settings/config.toml"
    template_file: str = "templates/ITMO_template.toml"

    def __init__(self, config_dir: str) -> None:
        """Initialize ConfigLoader with the base configuration file."""
        self.config_dir = Path(config_dir).resolve()
        self._load_config()
        self._load_settings()

    def _load_config(self) -> ArticleSettings:
        """Loads the base configuration file."""
        file_path_config = self._get_config_path(self.config_file)
        file_path_template = self._get_config_path(self.template_file)

        config_dict = self.file_handler.read(file_path_config)
        template_dict = self.file_handler.read(file_path_template)
        config_dict.update(template_dict)

        self.config = ArticleSettings.model_validate(config_dict)
        return self.config

    def _load_settings(self) -> dict[str, dict]:
        """Loads all TOML config files from ./config/settings/*.toml."""
        settings = self.config.model_dump()

        for key, file_path in settings["files"].items():
            if file_path.endswith(".toml"):
                file_path = (
                    self._get_config_path(f"settings/{file_path}")
                    if key == "prompts"
                    else get_resource_path(file_path=file_path)
                )
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
