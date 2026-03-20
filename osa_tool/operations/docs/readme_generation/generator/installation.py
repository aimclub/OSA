import os

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree
from osa_tool.tools.repository_analysis.dependencies import DependencyExtractor
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.utils import osa_project_root, parse_folder_name


class InstallationSectionBuilder:
    """
    Builder for generating installation instructions in a README or documentation.
    
        This class constructs formatted installation sections by combining template data with repository-specific information such as package metadata, Python version requirements, and installation commands.
    
        Methods:
        - __init__: Initializes the builder with configuration and repository data.
        - load_template: Loads and parses the TOML template file.
        - build_installation: Constructs the formatted installation section based on template and repo data.
        - _python_requires: Returns the Python version requirement string if specified.
        - _generate_install_command: Generates installation instructions using PyPI or from source.
    
        Attributes:
        - config_manager: Configuration manager providing access to settings.
        - repo_url: Git repository URL from git settings.
        - tree: SourceRank tree for the repository.
        - metadata: Repository metadata.
        - repo_path: Local path to the repository folder.
        - template_path: Path to the template TOML file.
        - _template: Loaded content of the template file.
        - info: PyPI package information including name, version, and downloads.
        - version: Python version requirement extracted from project files.
    """

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        """
        Initializes an InstallationSectionBuilder instance.
        
        Args:
            config_manager: Configuration manager providing access to settings.
            metadata: Repository metadata.
        
        Initializes the following instance attributes:
            config_manager (ConfigManager): Configuration manager instance.
            repo_url (str): Git repository URL from git settings.
            tree (SourceRank.tree): SourceRank tree for the repository.
            metadata (RepositoryMetadata): Repository metadata.
            repo_path (str): Local path to the repository folder, derived from the repository URL.
            template_path (str): Path to the template TOML file, located in the project's config/templates directory.
            _template (str): Loaded content of the template file.
            info (dict | None): PyPI package information including name, version, and downloads; None if the package is not published.
            version (str | None): Python version requirement extracted from project files (e.g., pyproject.toml or setup.py); None if not found.
        
        Why:
        - The repo_path is constructed by joining the current working directory with a folder name parsed from the repository URL, preparing for local repository operations.
        - The template_path is built relative to the project root to ensure the template file is reliably located.
        - The info attribute is populated by querying PyPI to gather publication details, which informs installation instructions.
        - The version attribute is extracted to determine Python version constraints, ensuring compatibility in generated documentation.
        """
        self.config_manager = config_manager
        self.repo_url = self.config_manager.get_git_settings().repository
        self.tree = SourceRank(self.config_manager).tree
        self.metadata = metadata
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.template_path = os.path.join(osa_project_root(), "config", "templates", "template.toml")
        self._template = self.load_template()
        self.info = PyPiPackageInspector(self.tree, self.repo_path).get_info()
        self.version = DependencyExtractor(self.tree, self.repo_path).extract_python_version_requirement()

    def load_template(self) -> dict:
        """
        Loads and parses the TOML template file from the specified path.
        
        This method reads the binary content of the template file and uses the `tomli` library
        to parse it into a Python dictionary. The parsed dictionary is typically used to
        populate or structure installation documentation sections.
        
        Args:
            self: The InstallationSectionBuilder instance containing the template_path attribute.
        
        Returns:
            A dictionary representing the parsed TOML content from the template file.
        """
        with open(self.template_path, "rb") as file:
            return tomli.load(file)

    def build_installation(self) -> str:
        """
        Constructs the formatted installation section based on template and repository data.
        
        This method composes the installation instructions for the project by combining
        prerequisite Python version information and the appropriate installation commands.
        It uses a template to ensure consistent formatting in the output documentation.
        
        Args:
            None.
        
        Returns:
            A formatted string containing the complete installation section. The string
            is built by populating a template with the project's Python version
            prerequisites, the project name, and the generated installation steps.
        """
        python_requirements = self._python_requires()
        install_cmd = self._generate_install_command()

        return self._template["installation"].format(
            prerequisites=python_requirements,
            project=self.config_manager.get_git_settings().name,
            steps=install_cmd,
        )

    def _python_requires(self) -> str:
        """
        Returns the Python version requirement string if specified, formatted as a Markdown note.
        
        If the version attribute is set, returns a Markdown-formatted string indicating the required Python version.
        If no version is specified, returns an empty string.
        
        Args:
            self: The InstallationSectionBuilder instance containing the version attribute.
        
        Returns:
            A Markdown-formatted prerequisite string if a version is set; otherwise, an empty string.
        """
        if not self.version:
            return ""

        return f"**Prerequisites:** requires Python {self.version}\n"

    def _generate_install_command(self) -> str:
        """
        Generates installation instructions using PyPI or from source.
        
        If the repository has package information available (via `self.info`), the instructions will use PyPI. Otherwise, instructions for building from source are provided, which include cloning the repository, navigating to the project directory, and optionally installing dependencies if a `requirements.txt` file is found in the repository.
        
        Args:
            None.
        
        Returns:
            A formatted string containing the installation instructions. The string includes markdown for headings and code blocks to present shell commands clearly.
        """
        if self.info:
            return f"**Using PyPi:**\n\n```sh\npip install {self.info.get('name')}\n```"

        steps = (
            f"**Build from source:**\n\n"
            f"1. Clone the {self.config_manager.get_git_settings().name} repository:\n"
            f"```sh\ngit clone {self.repo_url}\n```\n\n"
            f"2. Navigate to the project directory:\n"
            f"```sh\ncd {parse_folder_name(self.repo_url)}\n```\n\n"
        )

        req_path = find_in_repo_tree(self.tree, r"requirements\.txt")
        if req_path:
            steps += "3. Install the project dependencies:\n\n" "```sh\npip install -r requirements.txt\n```"

        return steps
