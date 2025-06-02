import os

import tomli

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.context.dependencies import DependencyExtractor
from osa_tool.readmegen.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.readmegen.utils import find_in_repo_tree
from osa_tool.utils import osa_project_root, parse_folder_name


class InstallationSectionBuilder:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.repo_url = self.config.git.repository
        self.tree = SourceRank(self.config_loader).tree
        self.metadata = load_data_metadata(self.repo_url)
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.template_path = os.path.join(
            osa_project_root(), "config", "templates", "template.toml"
        )
        self._template = self.load_template()
        self.info = PyPiPackageInspector(self.tree, self.repo_path).get_info()
        self.version = DependencyExtractor(
            self.tree, self.repo_path
        ).extract_python_version_requirement()

    def load_template(self) -> dict:
        """Loads and parses the TOML template file."""
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    def build_installation(self) -> str:
        """Constructs the formatted installation section based on template and repo data."""
        python_requirements = self._python_requires()
        install_cmd = self._generate_install_command()

        return self._template["installation"].format(
            prerequisites=python_requirements,
            project=self.config.git.name,
            steps=install_cmd,
        )

    def _python_requires(self) -> str:
        """Returns the Python version requirement string if specified."""
        if not self.version:
            return ""

        return f"**Prerequisites:** requires Python {self.version}\n"

    def _generate_install_command(self) -> str:
        """Generates installation instructions using PyPI or from source."""
        if self.info:
            return f"**Using PyPi:**\n\n```sh\npip install {self.info.get('name')}\n```"

        steps = (
            f"**Build from source:**\n\n"
            f"1. Clone the {self.config.git.name} repository:\n"
            f"```sh\ngit clone {self.repo_url}\n```\n\n"
            f"2. Navigate to the project directory:\n"
            f"```sh\ncd {parse_folder_name(self.repo_url)}\n```\n\n"
        )

        req_path = find_in_repo_tree(self.tree, r"requirements\.txt")
        if req_path:
            steps += (
                "3. Install the project dependencies:\n\n"
                "```sh\npip install -r requirements.txt\n```"
            )

        return steps
