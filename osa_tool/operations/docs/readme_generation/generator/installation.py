"""Build the README installation section."""

from __future__ import annotations

import os

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree
from osa_tool.tools.repository_analysis.dependencies import DependencyExtractor
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root, parse_folder_name


class InstallationSectionBuilder:
    """Generate installation instructions (pip or build-from-source)."""

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata) -> None:
        self.config_manager = config_manager
        self.metadata = metadata
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

        self.sourcerank = SourceRank(config_manager)
        self.tree = self.sourcerank.tree
        self.info = PyPiPackageInspector(self.tree, self.repo_path).get_info()
        self.version = DependencyExtractor(self.tree, self.repo_path).extract_python_version_requirement()

        self.template_path = os.path.join(osa_project_root(), "config", "templates", "template.toml")
        self._template = self.load_template()

    def load_template(self) -> dict:
        with open(self.template_path, "rb") as f:
            return tomli.load(f)

    def build_installation(self) -> str:
        logger.info("[InstallationBuilder] Building installation section")
        section = self._template["installation"].format(
            prerequisites=self._python_requires(),
            project=self.config_manager.get_git_settings().name,
            steps=self._generate_install_command(),
        )
        logger.info("[InstallationBuilder] Installation section built (%d chars)", len(section))
        return section

    def _python_requires(self) -> str:
        logger.debug("[InstallationBuilder] Resolving Python prerequisite text")
        if not self.version:
            logger.debug("[InstallationBuilder] Python version requirement not detected")
            return ""
        result = f"**Prerequisites:** requires Python {self.version}\n"
        logger.debug("[InstallationBuilder] Python prerequisite prepared: %s", self.version)
        return result

    def _generate_install_command(self) -> str:
        logger.debug("[InstallationBuilder] Building installation steps")
        if self.info:
            package_name = self.info.get("name")
            logger.info("[InstallationBuilder] Using PyPI installation path for package=%s", package_name)
            return f"**Using PyPi:**\n\n```sh\npip install {package_name}\n```"

        name = self.config_manager.get_git_settings().name
        folder = parse_folder_name(self.repo_url)
        logger.info("[InstallationBuilder] Using source installation path for repo=%s", self.repo_url)
        steps = (
            f"**Build from source:**\n\n"
            f"1. Clone the {name} repository:\n"
            f"```sh\ngit clone {self.repo_url}\n```\n\n"
            f"2. Navigate to the project directory:\n"
            f"```sh\ncd {folder}\n```\n\n"
        )
        if find_in_repo_tree(self.tree, r"requirements\.txt"):
            logger.info("[InstallationBuilder] requirements.txt detected; adding dependency install step")
            steps += "3. Install the project dependencies:\n\n```sh\npip install -r requirements.txt\n```"
        else:
            logger.debug("[InstallationBuilder] requirements.txt not found; skipping dependency install step")
        return steps
