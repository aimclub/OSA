import os
from unittest.mock import MagicMock

import pytest

from osa_tool.readmegen.context.files_contents import FileProcessor


@pytest.fixture
def mock_config_loader():
    mock_config_loader = MagicMock()
    mock_config_loader.config.git.repository = "https://github.com/user/repo"
    return mock_config_loader


@pytest.fixture
def mock_core_files():
    return ["file1.py", "file2.py", "file3.txt"]


def test_file_processor_initialization(mock_config_loader, mock_core_files):
    # Act
    processor = FileProcessor(
        config_loader=mock_config_loader, core_files=mock_core_files
    )
    # Assert
    assert processor.config.git.repository == "https://github.com/user/repo"
    assert processor.repo_path == os.path.join(os.getcwd(), "repo")


def test_process_files(mock_config_loader, mock_core_files):
    # Arrange
    processor = FileProcessor(
        config_loader=mock_config_loader, core_files=mock_core_files
    )
    # Act
    file_contexts = processor.process_files()
    # Assert
    assert len(file_contexts) == 3

    for file_context, file_path in zip(file_contexts, mock_core_files):
        assert file_context.path == file_path
        assert file_context.name == os.path.basename(file_path)


def test_create_file_context(mock_config_loader):
    # Arrange
    processor = FileProcessor(config_loader=mock_config_loader, core_files=[])
    # Act
    file_context = processor._create_file_context("file1.py")
    # Assert
    assert file_context.path == "file1.py"
    assert file_context.name == "file1.py"
