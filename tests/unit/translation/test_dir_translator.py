from pathlib import Path
from unittest.mock import patch, Mock, mock_open, call

import pytest

from osa_tool.operations.codebase.directory_translation.dirs_and_files_translator import RepositoryStructureTranslator
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


def test_init_sets_attributes(mock_config_manager):
    """
    Tests that the __init__ method of RepositoryStructureTranslator correctly sets its attributes.
    
    This test verifies that upon initialization, the translator object's fields are properly
    assigned based on the provided configuration manager. It checks the config_manager reference,
    repo_url, base_path, excluded_dirs, extensions_code_files, excluded_names, and the
    presence of a specific method on the model_handler.
    
    Args:
        mock_config_manager: A mocked or fixture-provided configuration manager object used to
            initialize the RepositoryStructureTranslator.
    
    The test initializes a RepositoryStructureTranslator and asserts the following class fields are set:
        config_manager: The configuration manager instance passed to the constructor.
        repo_url: The Git repository URL, sourced from the configuration manager's config.
        base_path: The filesystem path for the repository, ending with a folder name parsed from the repo_url.
            The folder name is derived by parsing the repository URL to ensure a safe, unique directory name.
        excluded_dirs: A set of directory names to exclude, initialized to {".git", ".venv"}.
            These are common directories that should not be processed for documentation.
        extensions_code_files: A set of file extensions considered as code files, initialized to {".py"}.
            This defines which file types are treated as source code.
        excluded_names: A collection of base names to exclude, which includes "readme".
            This prevents processing of common documentation files that are not source code.
        model_handler: An object possessing a 'send_request' method.
            This is required for the translator to interact with the underlying model for generating documentation.
    
    The test does not return a value.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)

    # Assert
    assert translator.config_manager == mock_config_manager
    assert translator.repo_url == mock_config_manager.config.git.repository
    assert translator.base_path.endswith(parse_folder_name(translator.repo_url))
    assert translator.excluded_dirs == {".git", ".venv"}
    assert translator.extensions_code_files == {".py"}
    assert "readme" in translator.excluded_names
    assert hasattr(translator.model_handler, "send_request")


def test_translate_text_excluded_name_returns_same(mock_config_manager):
    """
    Verifies that names included in the exclusion list are returned unchanged by the translation logic.
        
    This test ensures that the `RepositoryStructureTranslator` correctly identifies names that should not be processed by the LLM and returns them in their original form. This is important because certain names (like common technical terms or proper nouns) should be preserved without translation to maintain accuracy and consistency.
    
    Args:
        mock_config_manager: A mock object used to simulate the configuration management for the translator.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)

    # Assert
    for name in translator.excluded_names:
        assert translator._translate_text(name) == name


def test_translate_text_calls_model_handler(mock_config_manager):
    """
    Verifies that the `_translate_text` method correctly interacts with the model handler and processes the response.
    
    This test ensures that the `RepositoryStructureTranslator` properly delegates the translation task to its `model_handler`, calls the `send_request` method exactly once, and correctly formats the returned string by replacing spaces with underscores.
    
    Args:
        mock_config_manager: A mock object used to initialize the configuration settings for the translator.
    
    Returns:
        None.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)
    translator.model_handler.send_request = Mock(return_value="some text")

    # Act
    result = translator._translate_text("test")

    # Assert
    translator.model_handler.send_request.assert_called_once()
    assert result == "some_text"


@patch("os.walk")
def test_get_all_files_excludes_dirs(mock_walk, mock_config_manager):
    """
    Verifies that the _get_all_files method correctly retrieves file paths while excluding directory names from the results.
    
    This test ensures that the method filters out directory entries (including hidden directories like .git) and only returns actual file paths.
    
    Args:
        mock_walk: A mock object for the os.walk function used to simulate directory traversal and control test data.
        mock_config_manager: A mock object for the configuration manager used to initialize the translator.
    
    Returns:
        None.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)
    mock_walk.return_value = [
        ("/repo", (".git", "src"), ("file1.py", "file2.txt")),
        ("/repo/src", (), ("file3.py", "file4.txt")),
    ]

    # Act
    files = [str(Path(f)) for f in translator._get_all_files()]

    # Assert
    assert str(Path("/repo/src/file3.py")) in files
    assert str(Path("/repo/src/file4.txt")) in files
    assert not any(".git" in f for f in files)


@patch("os.walk")
def test_get_all_directories_excludes_dirs(mock_walk, mock_config_manager):
    """
    Verifies that the _get_all_directories method correctly filters out excluded directories like .git.
    
    This test ensures that directories specified in the exclusion list (such as version control directories) are not included in the directory listing, while other directories are retained.
    
    Args:
        mock_walk: A mock object for the os.walk function used to simulate file system traversal.
        mock_config_manager: A mock object for the configuration manager used to initialize the translator.
    
    Returns:
        None.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)
    mock_walk.return_value = [
        ("/repo", [".git", "src", "docs"], []),
        ("/repo/src", ["sub"], []),
        ("/repo/docs", [], []),
    ]

    # Act
    dirs = [str(Path(f)) for f in translator._get_all_directories()]

    # Assert
    assert all(".git" not in d for d in dirs)
    assert any("src" in d for d in dirs)
    assert any("docs" in d for d in dirs)


@pytest.mark.parametrize(
    "file_content,rename_map,expected_content",
    [
        (
            "import old_module\nfrom old_module.sub import something\npath='old_dir/file.txt'",
            {"old_module": "new_module", "old_dir": "new_dir", "file.txt": "file_new.txt"},
            "import new_module\nfrom new_module.sub import something\npath='new_dir/file_new.txt'",
        ),
        (
            "from a.b import c\nx = 'a/b/c.txt'",
            {"a": "x", "b": "y", "c.txt": "z.txt"},
            "from x.y import c\nx = 'x/y/z.txt'",
        ),
        (
            "import module1 as m\np = 'folder1/file1.csv'",
            {"module1": "mod_new", "folder1": "dir1", "file1.csv": "file1_new.csv"},
            "import mod_new as m\np = 'dir1/file1_new.csv'",
        ),
    ],
)
def test_update_code_parametrized(file_content, rename_map, expected_content):
    """
    Tests the update_code method with multiple input-output pairs.
    
    This method is a parameterized test that verifies the behavior of RepositoryStructureTranslator.update_code
    by mocking file operations and checking that the file content is correctly rewritten according to a rename mapping.
    It ensures that the method properly handles various patterns of import statements and path strings.
    
    Args:
        file_content: The initial content of the mock file to be processed.
        rename_map: A dictionary mapping old names to new names for replacement in the file content.
        expected_content: The expected content of the file after the update_code operation.
    
    Why:
    - This test validates that the update_code method correctly applies rename mappings across different code patterns,
      including imports, string literals, and function arguments.
    - It uses parameterization to efficiently test multiple scenarios in a single test method, ensuring robustness
      and reducing code duplication.
    - The test mocks file I/O to isolate the logic of update_code from actual filesystem operations, making the test
      fast, reliable, and independent of the environment.
    """
    # Arrange
    m = mock_open(read_data=file_content)

    with (
        patch("builtins.open", m),
        patch("osa_tool.operations.codebase.directory_translation.dirs_and_files_translator.logger") as mock_logger,
    ):
        # Act
        RepositoryStructureTranslator.update_code("dummy_path.py", rename_map)

    # Assert
    m.assert_called_with("dummy_path.py", "w", encoding="utf-8")
    handle = m()
    handle.write.assert_called_once_with(expected_content)

    mock_logger.info.assert_called_once()


def test_cycle_update_code_calls_update_code_for_all_files(mock_config_manager):
    """
    Verifies that the `_cycle_update_code` method correctly triggers code updates for every file in the repository.
    
    This test ensures that the translation process iterates through all discovered files and invokes the `update_code` logic with the provided rename mapping for each one. The test mocks the file list and the `update_code` method to isolate and verify the iteration behavior.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the translator.
    
    Why:
        This test confirms that the update cycle comprehensively processes all repository files, which is essential for ensuring complete structural translation when a rename mapping is applied.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)
    rename_map = {"a": "b"}
    files = ["file1.py", "file2.py"]

    translator._get_all_files = lambda: files

    with patch.object(RepositoryStructureTranslator, "update_code") as mock_update:
        # Act
        translator._cycle_update_code(rename_map)

    # Assert
    expected_calls = [call(f, rename_map) for f in files]
    mock_update.assert_has_calls(expected_calls, any_order=True)


def test_translate_directories(mock_config_manager):
    """
    Tests the translation of directory names within a repository structure.
    
    This test verifies that the `translate_directories` method correctly processes a list of directory paths, invokes the translation logic for each folder name, and returns a mapping of original names to their translated counterparts. It also ensures that the process is logged correctly.
    
    The test uses mocking to isolate the translation logic and logging, avoiding filesystem dependencies. This is why `os.path.exists` is patched and the translator's internal `_translate_text` method is replaced with a deterministic side effect.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the translator. This fixture provides the necessary configuration without relying on external files or settings.
    
    Returns:
        None: This method does not return a value.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)
    translator.base_path = Path("/repo")

    all_dirs = [Path("/repo/folder1"), Path("/repo/folder2")]

    with (
        patch.object(translator, "_translate_text", side_effect=lambda x: f"translated_{x}"),
        patch("os.path.exists", return_value=False),
        patch.object(logger, "info") as mock_logger,
    ):
        # Act
        result = translator.translate_directories([str(d) for d in all_dirs])

    # Assert
    expected = {"folder1": "translated_folder1", "folder2": "translated_folder2"}
    assert result == expected
    mock_logger.assert_called_with(f"Finished generating new names for {len(expected)} directories")


def test_translate_files(mock_config_manager):
    """
    Verifies that the repository structure translator correctly generates a mapping of original file paths to their translated counterparts.
    
    This test ensures the translator produces two distinct rename maps: one for full file paths and another for code references. It mocks the text translation to isolate the file renaming logic from actual content translation.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the translator.
    
    Returns:
        None.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)

    all_files = [Path("/repo/folder1/file1.py"), Path("/repo/folder2/file2.txt")]

    with (
        patch.object(translator, "_translate_text", side_effect=lambda x: f"translated_{Path(x).stem}"),
        patch("os.path.exists", return_value=False),
    ):
        # Act
        rename_map, rename_map_code = translator.translate_files([str(f) for f in all_files])

    # Assert
    expected_rename_map = {
        Path("/repo/folder1/file1.py").as_posix(): Path("/repo/folder1/translated_file1.py").as_posix(),
        Path("/repo/folder2/file2.txt").as_posix(): Path("/repo/folder2/translated_file2.txt").as_posix(),
    }
    expected_rename_map_code = {"file1": "translated_file1", "file2.txt": "translated_file2.txt"}
    rename_map_posix = {Path(k).as_posix(): Path(v).as_posix() for k, v in rename_map.items()}

    assert rename_map_posix == expected_rename_map
    assert rename_map_code == expected_rename_map_code


def test_rename_files_calls_os_rename_and_cycle_update(mock_config_manager):
    """
    Verifies that the rename_files method correctly triggers file renaming via os.rename and updates code cycles.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the translator.
    
    Note:
        This test ensures that the RepositoryStructureTranslator correctly identifies files, 
        translates their paths, executes the physical renaming on the file system, and 
        subsequently updates references within the code.
    
    Why:
        This test validates the integration of file translation, physical file system operations, and internal code reference updates. It confirms that the rename_files method orchestrates these steps correctly—translating file names, performing the actual OS rename operations, and then updating any code cycles (like import references) that depend on the renamed files. The mocking ensures the test isolates and verifies these interactions without affecting the real file system.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)
    translator.extensions_code_files = [".py"]

    files = [Path("/repo/folder1/file1.py"), Path("/repo/folder2/file2.txt")]

    with (
        patch.object(translator, "_get_all_files", return_value=files),
        patch.object(
            translator,
            "translate_files",
            return_value=(
                {
                    Path("/repo/folder1/file1.py"): Path("/repo/folder1/translated_file1.py"),
                    Path("/repo/folder2/file2.txt"): Path("/repo/folder2/translated_file2.txt"),
                },
                {"file1.py": "translated_file1.py", "file2.txt": "translated_file2.txt"},
            ),
        ),
        patch.object(translator, "_cycle_update_code") as mock_cycle,
        patch("os.rename") as mock_rename,
        patch.object(logger, "info") as mock_logger,
    ):
        # Act
        translator.rename_files()

    # Assert
    assert mock_cycle.call_count == 1
    assert mock_rename.call_count == 2
    mock_logger.assert_any_call("Files renaming completed successfully")


def test_rename_directories_calls_os_rename_and_cycle_update(mock_config_manager):
    """
    Verifies that the rename_directories method correctly triggers the directory renaming process, calls the OS rename function, and updates the code cycles.
    
    This test ensures the method orchestrates the full renaming workflow: it retrieves all directories, generates a translation map, performs the OS-level renames, and updates internal code references to reflect the new directory names.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the translator.
    
    Returns:
        None.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)
    translator.base_path = Path("/repo")

    all_dirs = [Path("/repo/folder1"), Path("/repo/folder2"), Path("/repo")]
    rename_map = {"folder1": "translated_folder1", "folder2": "translated_folder2"}

    with (
        patch.object(translator, "_get_all_directories", return_value=all_dirs),
        patch.object(translator, "translate_directories", return_value=rename_map),
        patch.object(translator, "_cycle_update_code") as mock_cycle,
        patch("os.rename") as mock_rename,
        patch.object(logger, "info") as mock_logger,
    ):
        # Act
        translator.rename_directories()

    # Assert
    assert mock_cycle.call_count == 1
    assert mock_rename.call_count == 2
    mock_logger.assert_any_call("Directory renaming completed successfully")


def test_rename_directories_and_files_calls_both_methods(mock_config_manager):
    """
    Verifies that the rename_directories_and_files method correctly triggers both directory and file renaming processes.
    
    This test ensures that when rename_directories_and_files is called, it internally invokes both the rename_directories and rename_files methods exactly once, confirming the integration of the two renaming operations.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the translator.
    
    Returns:
        None.
    """
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)

    with (
        patch.object(translator, "rename_directories") as mock_dirs,
        patch.object(translator, "rename_files") as mock_files,
    ):
        # Act
        translator.rename_directories_and_files()

    # Assert
    assert mock_dirs.call_count == 1
    assert mock_files.call_count == 1
