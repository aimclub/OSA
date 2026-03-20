from unittest.mock import patch

from osa_tool.operations.docs.readme_generation.context.files_contents import FileProcessor, FileContext


def test_file_processor_initialization(mock_config_manager):
    """
    Verifies that the FileProcessor class is correctly initialized with the provided configuration and file list.
    
    Args:
        mock_config_manager: A mocked configuration manager object used to provide settings for the processor. The test uses its configuration to check the processor's repo_url attribute.
    
    Returns:
        None.
    
    Why:
        This test ensures that the FileProcessor constructor properly assigns the given configuration manager and file list, and that internal attributes like repo_url and length_of_content are set to expected values. It validates the initialization logic of the FileProcessor, which is foundational for subsequent processing operations in the OSA Tool.
    """
    # Arrange
    core_files = ["file1.py", "dir/file2.txt"]
    processor = FileProcessor(mock_config_manager, core_files)

    # Assert
    assert processor.config_manager == mock_config_manager
    assert processor.core_files == core_files
    assert processor.repo_url == mock_config_manager.config.git.repository
    assert processor.length_of_content == 50_000


@patch("osa_tool.operations.docs.readme_generation.context.files_contents.read_file")
def test_create_file_context_truncates_content(mock_read_file, mock_config_manager):
    """
    Verifies that the `_create_file_context` method correctly truncates file content when it exceeds the maximum allowed length.
    
    Args:
        mock_read_file: A mock object for the file reading utility, patched to return a long string.
        mock_config_manager: A mock object for the configuration manager, used to initialize the FileProcessor.
    
    Why:
    This test ensures that the file processor enforces a content length limit by truncating overly long file contents, preventing excessive memory usage or processing overhead when generating documentation context.
    
    Returns:
        None.
    """
    # Arrange
    mock_read_file.return_value = "a" * 100_000
    core_files = ["file1.py"]
    processor = FileProcessor(mock_config_manager, core_files)

    # Act
    file_context = processor._create_file_context("file1.py")

    # Assert
    assert isinstance(file_context, FileContext)
    assert file_context.path == "file1.py"
    assert file_context.name == "file1.py"
    assert len(file_context.content) == processor.length_of_content
    assert file_context.content == "a" * processor.length_of_content


@patch("osa_tool.operations.docs.readme_generation.context.files_contents.read_file")
def test_process_files_returns_file_context_list(mock_read_file, mock_config_manager):
    """
    Verifies that the process_files method correctly returns a list of FileContext objects.
    
    This test ensures that the FileProcessor correctly iterates over the provided file paths,
    reads their content using the mocked file reader, and encapsulates the results into
    FileContext instances with the expected paths and contents.
    
    Args:
        mock_read_file: A mock object for the file reading utility, patched to return predefined content.
        mock_config_manager: A mock object for the configuration manager, used to instantiate the FileProcessor.
    
    Why:
        This test validates the core functionality of FileProcessor.process_files, which is responsible for reading file contents and packaging them into structured objects for further processing in the documentation pipeline. Mocking external dependencies isolates the test to the unit's logic.
    """
    # Arrange
    mock_read_file.side_effect = ["content1", "content2"]
    core_files = ["file1.py", "file2.py"]
    processor = FileProcessor(mock_config_manager, core_files)

    # Act
    result = processor.process_files()

    # Asert
    assert len(result) == 2
    assert all(isinstance(f, FileContext) for f in result)
    assert result[0].path == "file1.py"
    assert result[0].content == "content1"
    assert result[1].path == "file2.py"
    assert result[1].content == "content2"
