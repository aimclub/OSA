from unittest.mock import patch

from osa_tool.readmegen.context.files_contents import FileProcessor, FileContext


def test_file_processor_initialization(mock_config_loader):
    # Arrange
    core_files = ["file1.py", "dir/file2.txt"]
    processor = FileProcessor(mock_config_loader, core_files)

    # Assert
    assert processor.config == mock_config_loader.config
    assert processor.core_files == core_files
    assert processor.repo_url == mock_config_loader.config.git.repository
    assert processor.length_of_content == 50_000


@patch("osa_tool.readmegen.context.files_contents.read_file")
def test_create_file_context_truncates_content(mock_read_file, mock_config_loader):
    # Arrange
    mock_read_file.return_value = "a" * 100_000
    core_files = ["file1.py"]
    processor = FileProcessor(mock_config_loader, core_files)

    # Act
    file_context = processor._create_file_context("file1.py")

    # Assert
    assert isinstance(file_context, FileContext)
    assert file_context.path == "file1.py"
    assert file_context.name == "file1.py"
    assert len(file_context.content) == processor.length_of_content
    assert file_context.content == "a" * processor.length_of_content


@patch("osa_tool.readmegen.context.files_contents.read_file")
def test_process_files_returns_file_context_list(mock_read_file, mock_config_loader):
    # Arrange
    mock_read_file.side_effect = ["content1", "content2"]
    core_files = ["file1.py", "file2.py"]
    processor = FileProcessor(mock_config_loader, core_files)

    # Act
    result = processor.process_files()

    # Asert
    assert len(result) == 2
    assert all(isinstance(f, FileContext) for f in result)
    assert result[0].path == "file1.py"
    assert result[0].content == "content1"
    assert result[1].path == "file2.py"
    assert result[1].content == "content2"
