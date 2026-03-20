import os

from pydantic import BaseModel

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.docs.readme_generation.utils import read_file
from osa_tool.utils.utils import parse_folder_name


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


    def __init__(self, config_manager: ConfigManager, core_files: list[str]):
        """
        Initializes the FileProcessor instance.
        
        Args:
            config_manager: Manages configuration settings for the analysis.
            core_files: List of core file paths to be analyzed.
        
        Initializes the following class fields:
            config_manager: Manages configuration settings for the analysis.
            core_files: List of core file paths to be analyzed.
            repo_url: URL of the Git repository, derived from the configuration's Git settings.
            repo_path: Local filesystem path where the repository is or will be located. This is constructed by joining the current working directory with a folder name parsed from the repository URL.
            length_of_content: Maximum length of content to process, set to 50,000. This limit is used to constrain the amount of data processed in a single operation for performance and memory management.
        """
        self.config_manager = config_manager
        self.core_files = core_files
        self.repo_url = self.config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.length_of_content = 50_000

    def process_files(self) -> list[FileContext]:
        """
        Generate file info for the given repository path.
        
        Processes all core files in the repository by creating a FileContext object for each one. This method iterates through the list of file paths stored in the instance's `core_files` attribute and applies the internal helper to read and truncate each file's content. The purpose is to collect structured metadata and limited content for all relevant files in a single operation, enabling batch analysis and documentation generation.
        
        Args:
            None. Uses the instance's `core_files` attribute as the source of file paths.
        
        Returns:
            A list of FileContext objects, each containing a file's relative path, base name, and truncated content.
        """
        return [self._create_file_context(file_path) for file_path in self.core_files]

    def _create_file_context(self, file_path: str) -> FileContext:
        """
        Create a file context object for the given file path.
        
        Reads the file content from the repository, truncating it to a maximum length specified by the instance's `length_of_content` attribute. This is done to limit memory usage and processing time when handling large files. The method constructs an absolute path by joining the repository root path with the provided relative file path.
        
        Args:
            file_path: The relative path of the file within the repository.
        
        Returns:
            A FileContext object containing the file's relative path, base name, and truncated content.
        """
        abs_file_path = os.path.join(self.repo_path, file_path)
        content = read_file(abs_file_path)[: self.length_of_content]
        return FileContext(path=file_path, name=os.path.basename(file_path), content=content)

    @staticmethod
    def serialize_file_contexts(files: list[FileContext]) -> str:
        """
        Serializes a list of FileContext objects into a string for unified display or output.
        
        The method joins multiple file representations into a single, formatted string, making it easier to output or log the combined file information in a structured way. Each file is presented in a clear, sectioned format to distinguish between different files and their details.
        
        Args:
            files: A list of FileContext objects representing the files to serialize.
        
        Returns:
            A string where each file is represented as a section starting with "###", followed by the file's name and path in parentheses, and then the file's content. Sections are separated by double newlines.
        """
        return "\n\n".join(f"### {f.name} ({f.path})\n{f.content}" for f in files)
