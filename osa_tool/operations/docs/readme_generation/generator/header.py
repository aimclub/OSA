import json
import os

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.tools.repository_analysis.dependencies import DependencyExtractor
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.utils import osa_project_root, parse_folder_name


class HeaderBuilder:
    """
    HeaderBuilder constructs the header section of a README file by generating and formatting badges for project information and technologies.
    
        Class Methods:
        - __init__: Initializes the HeaderBuilder with necessary configuration and data.
        - load_template: Loads and parses the TOML template file.
        - load_tech_icons: Loads technology icons from a JSON file.
        - build_header: Builds the full header section for the README file.
        - build_information_section: Builds the section with PyPi and license badges.
        - build_technology_section: Builds the section with technology badges based on project dependencies.
        - generate_info_badges: Generates PyPi-related badges: version and download stats.
        - generate_license_badge: Generates a license badge using Shields.io.
        - generate_tech_badges: Generates badges for technologies used in the project using available icons.
    
        Class Attributes:
        - config_manager: Configuration manager instance.
        - repo_url: URL of the Git repository, derived from git settings.
        - repo_path: Local filesystem path where the repository is located.
        - tree: SourceRank tree structure for the repository.
        - metadata: Provided repository metadata.
        - template_path: Filesystem path to the TOML template file.
        - icons_tech_path: Filesystem path to the shields.io icons JSON file.
        - max_tech_badges: Maximum number of technology badges to display.
        - _template: Loaded content of the template file.
        - info: PyPI package information, including name, version, and download count.
        - techs: Set of technology names extracted from project dependencies.
    
        The methods handle loading templates and icons, constructing badge sections, and assembling the final header. The attributes store configuration, repository data, template content, and badge information for generating the README header.
    """

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        """
        Initializes the HeaderBuilder instance.
        
        Args:
            config_manager: Configuration manager providing access to settings.
            metadata: Metadata about the repository.
        
        Initializes the following instance attributes:
            config_manager (ConfigManager): Configuration manager instance.
            repo_url (str): URL of the Git repository, derived from git settings.
            repo_path (str): Local filesystem path where the repository is located, constructed by joining the current working directory with a folder name parsed from the repository URL.
            tree (SourceRank): SourceRank tree structure for the repository, used for analyzing project structure and dependencies.
            metadata (RepositoryMetadata): Provided repository metadata.
            template_path (str): Filesystem path to the TOML template file, located in the project's config/templates directory.
            icons_tech_path (str): Filesystem path to the shields.io icons JSON file, located in the project's operations/docs/readme_generation/generator/icons directory.
            max_tech_badges (int): Maximum number of technology badges to display (default: 7).
            _template (str): Loaded content of the template file.
            info (dict | None): PyPI package information, including name, version, and download count; None if the package is not published on PyPI.
            techs (set[str]): Set of technology names extracted from project dependencies, used for generating technology badges in the header.
        """
        self.config_manager = config_manager
        self.repo_url = self.config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.tree = SourceRank(self.config_manager).tree
        self.metadata = metadata
        self.template_path = os.path.join(osa_project_root(), "config", "templates", "template.toml")
        self.icons_tech_path = os.path.join(
            osa_project_root(),
            "operations",
            "docs",
            "readme_generation",
            "generator",
            "icons",
            "shieldsio_icons.json",
        )
        self.max_tech_badges = 7
        self._template = self.load_template()
        self.info = PyPiPackageInspector(self.tree, self.repo_path).get_info()
        self.techs = DependencyExtractor(self.tree, self.repo_path).extract_techs()

    def load_template(self) -> dict:
        """
        Loads and parses the TOML template file.
        
        Args:
            template_path: The file system path to the TOML template file to be loaded.
        
        Returns:
            A dictionary representing the parsed contents of the TOML file.
        
        Why:
            This method reads a TOML configuration file that serves as a template for generating documentation or repository structures. Loading it as a dictionary allows the tool to programmatically access and utilize the template's defined settings and content structure in subsequent enhancement operations.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    def load_tech_icons(self) -> dict:
        """
        Loads technology icons from a JSON file.
        
        Args:
            self: The instance of the HeaderBuilder class.
        
        Returns:
            A dictionary containing the parsed JSON data from the technology icons file.
        
        Raises:
            FileNotFoundError: If the JSON file specified by `self.icons_tech_path` does not exist.
            ValueError: If the JSON file exists but contains invalid JSON syntax.
        
        Why:
            This method provides a centralized way to load icon configuration data needed for building headers or UI components. It validates both file existence and JSON integrity to ensure robust handling of external configuration files.
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
        Builds the full header section for the README file.
        
        This method combines the project name, information badges, and technology badges
        into a formatted string by populating a header template. The project name is
        retrieved from the Git configuration, and the badge sections are generated by
        the class's own helper methods.
        
        Returns:
            str: A formatted string representing the header section of the README.
        """
        return self._template["headers"].format(
            project_name=self.config_manager.get_git_settings().name,
            info_badges=self.build_information_section,
            tech_badges=self.build_technology_section,
        )

    @property
    def build_information_section(self) -> str:
        """
        Builds the section containing PyPI and license badges for the project header.
        
        This property assembles the badges generated by `generate_info_badges` (PyPI version and download stats) and `generate_license_badge` into a formatted string using a predefined template. The resulting section is intended for inclusion in documentation like a README to visually convey key project metadata and licensing information.
        
        Why:
        - Centralizes the creation of a standardized information badge section, ensuring consistent formatting.
        - Enhances project documentation by providing immediate visibility of version, download statistics, and license status through clickable badges.
        
        Returns:
            A formatted string containing the combined badges, ready for insertion into the documentation template.
        """
        badges_data = self.generate_info_badges() + self.generate_license_badge()
        return self._template["information_badges"].format(badges_data=badges_data)

    @property
    def build_technology_section(self) -> str:
        """
        Builds the section with technology badges based on project dependencies.
        
        This property returns a formatted string for the technology badge section by using the badges generated by `generate_tech_badges`. The output is inserted into a predefined template to produce the final markdown for the documentation header.
        
        Why:
            Including a technology badge section provides a quick, visual overview of the project's key technologies, improving the readability and attractiveness of the documentation. The method relies on the helper function to ensure only relevant and sufficiently numerous badges are displayed.
        
        Returns:
            A formatted string containing the technology badge section in markdown, ready for insertion into the documentation header. If `generate_tech_badges` returns an empty string, this section will be empty as well.
        """
        badges_data = self.generate_tech_badges()
        return self._template["technology_badges"].format(technology_badges=badges_data)

    def generate_info_badges(self) -> str:
        """
        Generates PyPi-related badges for the project: version badge from PyPI and download stats badge from PePy.
        
        This method constructs Markdown badge links based on the project's metadata. It returns an empty string if no project info is available. The badges are only added when the relevant data (name, version, downloads) is present in the info dictionary.
        
        Args:
            None: Uses the instance's `self.info` dictionary, which should contain PyPI project metadata.
        
        Returns:
            A string containing one or two Markdown badge links separated by newlines, or an empty string if no badges can be generated.
        
        Why:
        - The version badge links to the project's PyPI release page, providing quick access to the latest version.
        - The downloads badge links to PePy statistics, offering visibility into the project's usage and popularity.
        - Badges are a common way to visually convey key project metrics directly in documentation like README files.
        """
        if not self.info:
            return ""

        name = self.info.get("name")
        version = self.info.get("version")
        downloads = self.info.get("downloads")
        badges = []

        if name and version:
            badges.append(f"[![PyPi](https://badge.fury.io/py/{name}.svg)](https://badge.fury.io/py/{name})")

        if name and downloads is not None:
            badges.append(f"[![Downloads](https://static.pepy.tech/badge/{name})](https://pepy.tech/project/{name})")

        return "\n".join(badges)

    def generate_license_badge(self) -> str:
        """
        Generates a license badge using Shields.io.
        
        This method constructs a badge that visually indicates the project's license,
        enhancing the README or documentation with a clickable, standardized license
        indicator. It is used to improve project transparency and accessibility by
        providing a quick reference to the licensing terms.
        
        Args:
            None: This method uses instance attributes from `self.metadata` and
            `self.config_manager`.
        
        Returns:
            A string containing the HTML markup for the license badge, or an empty
            string if no license name is defined in the metadata. The badge URL is
            dynamically built using the repository's host platform and full name
            from the Git settings, along with a predefined style and color.
        """
        if not self.metadata.license_name:
            return ""
        badge_style = "flat"
        badge_color = "blue"

        badge_url = (
            f"https://img.shields.io/{self.config_manager.get_git_settings().host}/license/{self.config_manager.get_git_settings().full_name}"
            f"?style={badge_style}&logo=opensourceinitiative&logoColor=white&color={badge_color}"
        )
        badge_html = f"\n![License]({badge_url})"
        return badge_html

    def generate_tech_badges(self) -> str:
        """
        Generates badges for technologies used in the project using available icons.
        
        The method creates a markdown-formatted string of badges for technologies listed in `self.techs`. It sorts the technologies alphabetically and includes only those with an available icon. If the number of valid badges is too low, an empty string is returned to avoid displaying sparse badge sections.
        
        Args:
            self: The instance of the HeaderBuilder class.
        
        Returns:
            A markdown string containing a "Built with:" line followed by badge images, or an empty string if no badges are generated. Returns an empty string if `self.techs` is empty, if fewer than three badges are produced, or if the maximum badge limit is reached before any badges are added.
        
        Why:
            This provides a visual, standardized way to showcase project technologies in documentation headers. The sorting ensures consistent ordering, and the minimum badge threshold prevents cluttered or insignificant badge displays.
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
