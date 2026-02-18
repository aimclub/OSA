import os

from pydantic import BaseModel

from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.utils import read_file
from osa_tool.utils import parse_folder_name


class FileContext(BaseModel):
    """
    FileContext model for storing file information.
    """

    path: str
    name: str
    content: str


class FileProcessor:
    """
    File processor class to process files in a repository.
    """

    def __init__(self, config_loader: ConfigLoader, core_files: list[str]):
        """
        Initializes the repository configuration and related attributes.
        
        Args:
            config_loader: An instance of ConfigLoader that provides the configuration
                data for the repository.
            core_files: A list of strings representing the core file paths to be
                processed.
        
        Attributes:
            config: The configuration dictionary obtained from the config_loader.
            core_files: The list of core file paths passed to the constructor.
            repo_url: The Git repository URL extracted from the configuration.
            repo_path: The absolute path to the repository directory, derived from
                the current working directory and the parsed folder name of the
                repository URL.
            length_of_content: A fixed integer (50,000) representing the maximum
                length of content to be handled.
        
        Returns:
            None
        """
        self.config = config_loader.config
        self.core_files = core_files
        self.repo_url = self.config.git.repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.length_of_content = 50_000

    def process_files(self) -> list[FileContext]:
        """Generate file info for the given repository path."""
        return [self._create_file_context(file_path) for file_path in self.core_files]

    def _create_file_context(self, file_path: str) -> FileContext:
        """Create a file context object for the given file path."""
        abs_file_path = os.path.join(self.repo_path, file_path)
        content = read_file(abs_file_path)[: self.length_of_content]
        return FileContext(path=file_path, name=os.path.basename(file_path), content=content)
