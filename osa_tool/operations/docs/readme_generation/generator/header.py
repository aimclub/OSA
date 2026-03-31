"""Build the README header section (project name, info badges, tech badges)."""

from __future__ import annotations

import json
import os
from functools import cached_property

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.tools.repository_analysis.dependencies import DependencyExtractor
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.utils import osa_project_root, parse_folder_name


class HeaderBuilder:
    """Produce the top-of-README header with project name, info badges, and tech badges."""

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata) -> None:
        self.config_manager = config_manager
        self.metadata = metadata
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.max_tech_badges = 7

        self.tree = SourceRank(config_manager).tree
        self.info = PyPiPackageInspector(self.tree, self.repo_path).get_info()
        self.techs = DependencyExtractor(self.tree, self.repo_path).extract_techs()

        self.template_path = os.path.join(osa_project_root(), "config", "templates", "template.toml")
        self.icons_tech_path = os.path.join(
            osa_project_root(), "operations", "docs", "readme_generation", "generator", "icons", "shieldsio_icons.json"
        )
        self._template = self.load_template()

    def load_template(self) -> dict:
        with open(self.template_path, "rb") as f:
            return tomli.load(f)

    @cached_property
    def _tech_icons(self) -> dict:
        """Load tech icons once and cache."""
        return self.load_tech_icons()

    def load_tech_icons(self) -> dict:
        if not os.path.exists(self.icons_tech_path):
            raise FileNotFoundError(f"Icon file not found: {self.icons_tech_path}")
        with open(self.icons_tech_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def build_header(self) -> str:
        return self._template["headers"].format(
            project_name=self.config_manager.get_git_settings().name,
            info_badges=self.build_information_section,
            tech_badges=self.build_technology_section,
        )

    @property
    def build_information_section(self) -> str:
        badges = self.generate_info_badges() + self.generate_license_badge()
        return self._template["information_badges"].format(badges_data=badges)

    @property
    def build_technology_section(self) -> str:
        badges = self.generate_tech_badges()
        return self._template["technology_badges"].format(technology_badges=badges)

    def generate_info_badges(self) -> str:
        if not self.info:
            return ""
        name = self.info.get("name")
        version = self.info.get("version")
        downloads = self.info.get("downloads")
        parts: list[str] = []
        if name and version:
            parts.append(f"[![PyPi](https://badge.fury.io/py/{name}.svg)](https://badge.fury.io/py/{name})")
        if name and downloads is not None:
            parts.append(f"[![Downloads](https://static.pepy.tech/badge/{name})](https://pepy.tech/project/{name})")
        return "\n".join(parts)

    def generate_license_badge(self) -> str:
        if not self.metadata.license_name:
            return ""
        git = self.config_manager.get_git_settings()
        url = (
            f"https://img.shields.io/{git.host}/license/{git.full_name}"
            f"?style=flat&logo=opensourceinitiative&logoColor=white&color=blue"
        )
        return f"\n![License]({url})"

    def generate_tech_badges(self) -> str:
        if not self.techs:
            return ""
        icons = self._tech_icons
        badges: list[str] = ["Built with:\n"]
        for tech in sorted(self.techs):
            if tech in icons:
                badges.append(f"![{tech}]({icons[tech][0]})")
            if len(badges) >= self.max_tech_badges + 1:
                break
        return "\n".join(badges) if len(badges) > 3 else ""
