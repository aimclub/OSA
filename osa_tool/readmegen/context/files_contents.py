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
        self.config = config_loader.config
        self.core_files = core_files
        self.repo_url = self.config.git.repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

    def process_files(self) -> list[FileContext]:
        """Generate file info for the given repository path."""
        return [
            self._create_file_context(file_path)
            for file_path in self.core_files
        ]

    def _create_file_context(self, file_path: str) -> FileContext:
        """Create a file context object for the given file path."""
        abs_file_path = os.path.join(self.repo_path, file_path)
        content = read_file(abs_file_path)[:50000]
        return FileContext(
            path=file_path,
            name=os.path.basename(file_path),
            content=content
        )
