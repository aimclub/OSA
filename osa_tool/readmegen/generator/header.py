import json
import os

import tomli

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.context.dependencies import DependencyExtractor
from osa_tool.readmegen.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.utils import osa_project_root, parse_folder_name


class HeaderBuilder:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.repo_url = self.config.git.repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.tree = SourceRank(self.config_loader).tree
        self.metadata = load_data_metadata(self.repo_url)
        self.template_path = os.path.join(
            osa_project_root(),
            "config",
            "templates",
            "template.toml"
        )
        self.icons_tech_path = os.path.join(
            osa_project_root(),
            "readmegen",
            "generator",
            "icons",
            "shieldsio_icons.json"
        )
        self.max_tech_badges = 7
        self._template = self.load_template()
        self.info = PyPiPackageInspector(self.tree, self.repo_path).get_info()
        self.techs = DependencyExtractor(self.tree, self.repo_path).extract_techs()

    def load_template(self) -> dict:
        """
        Loads a TOML template file and returns its sections as a dictionary.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    def load_tech_icons(self) -> dict:
        """
        Loads technology icons data from a JSON file.

        Returns:
            dict: Dictionary with technology names as keys and badge URLs as values.
        """
        if not os.path.exists(self.icons_tech_path):
            raise FileNotFoundError(f"Icon file not found at: {self.icons_tech_path}")

        with open(self.icons_tech_path, "r", encoding="utf-8") as file:
            try:
                data = json.load(file)
                return data
            except json.JSONDecodeError as e:
                raise ValueError(f"Error decoding JSON file: {e}")

    def build_header(self) -> str:
        """
        Builds the full header section for the README file, combining the project name,
        information badges, and technology badges into a formatted string.

        Returns:
            str: A formatted string representing the header section of the README.
        """
        return self._template["headers"].format(
            project_name=self.config.git.name,
            info_badges=self.build_information_section,
            tech_badges=self.build_technology_section
        )

    @property
    def build_information_section(self) -> str:
        """
        Builds the information section for the README, including badges for project
        name, version, and download statistics.

        Returns:
            str: Formatted string with project information badges.
        """
        badges_data = self.generate_info_badges() + self.generate_license_badge()
        return self._template["information_badges"].format(badges_data=badges_data)

    @property
    def build_technology_section(self) -> str:
        """
        Builds the technology section for the README, including badges for technologies
        used in the project, based on the extracted technology names.

        Returns:
            str: Formatted string with technology badges.
        """
        badges_data = self.generate_tech_badges()
        return self._template["technology_badges"].format(technology_badges=badges_data)

    def generate_info_badges(self) -> str:
        """
        Generates badges related to PyPi project information, such as the project name,
        version, and downloads.

        Returns:
            str: Formatted string with PyPi-related badges.
        """
        if not self.info:
            return ""

        name = self.info.get("name")
        version = self.info.get("version")
        downloads = self.info.get("downloads")
        badges = []

        if name and version:
            badges.append(
                f"[![PyPi](https://badge.fury.io/py/{name}.svg)](https://badge.fury.io/py/{name})"
            )

        if name and downloads is not None:
            badges.append(
                f"[![Downloads](https://static.pepy.tech/badge/{name})](https://pepy.tech/project/{name})"
            )

        return "\n".join(badges)

    def generate_license_badge(self) -> str:
        if not self.metadata.license_name:
            return ""
        badge_style = "flat"
        badge_color = "blue"

        badge_url = (f"https://img.shields.io/{self.config.git.host}/license/{self.config.git.full_name}"
                     f"?style={badge_style}&logo=opensourceinitiative&logoColor=white&color={badge_color}")
        badge_html = f"\n![License]({badge_url})"
        return badge_html

    def generate_tech_badges(self) -> str:
        """
        Generates badges for the technologies used in the repository, based on the
        extracted technology names and available icons.

        Returns:
            str: Formatted string with technology badges.
        """
        if not self.techs:
            return ""

        sorted_techs = sorted(self.techs)

        badges = ["Built with:\n"]
        for tech in sorted_techs:
            if tech in self.load_tech_icons():
                badge_url = self.load_tech_icons()[tech][0]
                badges.append(f"![{tech}]({badge_url})")

            if len(badges) >= self.max_tech_badges + 1:
                break
        if len(badges) <= 3:
            return ""
        return "\n".join(badges)
