import os
from unittest.mock import MagicMock

import pytest

from osa_tool.readmegen.context.files_contents import FileProcessor


@pytest.fixture
def mock_config_loader():
    """
    Creates a mock configuration loader with a predefined repository URL.
    
    Returns:
        MagicMock: A mock object where the `config.git.repository` attribute is set
        to 'https://github.com/user/repo'.
    """
    mock_config_loader = MagicMock()
    mock_config_loader.config.git.repository = "https://github.com/user/repo"
    return mock_config_loader


@pytest.fixture
def mock_core_files():
    """
    Return a list of mock core file names.
    
    This function provides a hard‑coded list of filenames that represent
    core files used in testing or demonstration scenarios. The list
    contains three entries: 'file1.py', 'file2.py', and 'file3.txt'.
    
    Returns:
        list[str]: A list of file name strings.
    """
    return ["file1.py", "file2.py", "file3.txt"]


def test_file_processor_initialization(mock_config_loader, mock_core_files):
    """
    Test the initialization of FileProcessor.
    
    Parameters
    ----------
    mock_config_loader
        Mock configuration loader used to instantiate FileProcessor.
    mock_core_files
        Mock core files used to instantiate FileProcessor.
    
    Returns
    -------
    None
    
    This test verifies that the FileProcessor correctly sets its configuration and repository path upon initialization. It asserts that the git repository URL in the processor's config matches the expected value and that the repo_path attribute is set to the current working directory joined with 'repo'.
    """
    # Act
    processor = FileProcessor(config_loader=mock_config_loader, core_files=mock_core_files)
    # Assert
    assert processor.config.git.repository == "https://github.com/user/repo"
    assert processor.repo_path == os.path.join(os.getcwd(), "repo")


def test_process_files(mock_config_loader, mock_core_files):
    """
    Test that FileProcessor.process_files correctly processes files.
    
    Args:
        mock_config_loader: A mock configuration loader used to initialize the FileProcessor.
        mock_core_files: A list of file paths that represent the core files to be processed.
    
    Returns:
        None
    """
    # Arrange
    processor = FileProcessor(config_loader=mock_config_loader, core_files=mock_core_files)
    # Act
    file_contexts = processor.process_files()
    # Assert
    assert len(file_contexts) == 3

    for file_context, file_path in zip(file_contexts, mock_core_files):
        assert file_context.path == file_path
        assert file_context.name == os.path.basename(file_path)


def test_create_file_context(mock_config_loader):
    """
    Test that FileProcessor._create_file_context correctly initializes a FileContext with the given file path.
    
    Args:
        mock_config_loader: A mock configuration loader used to instantiate FileProcessor.
    
    Returns:
        None
    """
    # Arrange
    processor = FileProcessor(config_loader=mock_config_loader, core_files=[])
    # Act
    file_context = processor._create_file_context("file1.py")
    # Assert
    assert file_context.path == "file1.py"
    assert file_context.name == "file1.py"
