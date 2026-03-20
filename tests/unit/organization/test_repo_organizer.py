from unittest.mock import patch

import pytest

from osa_tool.operations.codebase.organization.repo_organizer import RepoOrganizer


def _fix_paths(repo, tmp_path):
    """
    Updates the directory paths for a repository object based on a temporary path.
    
    WHY: When a repository is cloned or processed into a temporary location, its original directory paths (like tests_dir and examples_dir) may no longer be valid. This method reassigns those paths to point to the correct subdirectories within the new temporary workspace, ensuring subsequent operations can locate the tests and examples folders.
    
    Args:
        repo: The repository object whose paths need to be updated.
        tmp_path: The base temporary path used to construct the new directory strings.
    
    Attributes:
        repo.tests_dir: The absolute path to the tests directory within the temporary path.
        repo.examples_dir: The absolute path to the examples directory within the temporary path.
    """
    repo.tests_dir = str(tmp_path / "tests")
    repo.examples_dir = str(tmp_path / "examples")


def test_add_directories_creates_missing(mock_config_manager, tmp_path):
    """
    Tests that add_directories creates missing directories.
    
    WHY: This test verifies that the RepoOrganizer's add_directories method correctly creates the 'tests' and 'examples' directories when they do not already exist in the repository. It ensures the method handles missing directories as intended, which is essential for maintaining a consistent repository structure.
    
    Args:
        mock_config_manager: A mocked configuration manager for the repository.
        tmp_path: A temporary path used for testing, representing the repository's location.
    
    Returns:
        None
    """
    # Arrange
    repo = RepoOrganizer(mock_config_manager)
    repo.repo_path = str(tmp_path)
    _fix_paths(repo, tmp_path)

    tests_dir = tmp_path / "tests"
    examples_dir = tmp_path / "examples"

    with patch("osa_tool.operations.codebase.organization.repo_organizer.logger") as mock_logger:
        # Act
        repo.add_directories()

        # Assert
        assert tests_dir.exists()
        assert examples_dir.exists()
        assert any("Created directory" in str(c.args[0]) for c in mock_logger.info.call_args_list)


def test_add_directories_when_already_exist(mock_config_manager, tmp_path):
    """
    Tests the behavior of `add_directories` when the target directories already exist.
    
    WHY: This test verifies that the method handles the case where the directories it intends to create are already present, ensuring it logs an appropriate message instead of raising an error or attempting to recreate them.
    
    Args:
        mock_config_manager: A mocked configuration manager object for the repository organizer.
        tmp_path: A temporary path object used as the base directory for the test.
    
    Returns:
        None
    """
    # Arrange
    repo = RepoOrganizer(mock_config_manager)
    repo.repo_path = str(tmp_path)
    _fix_paths(repo, tmp_path)

    (tmp_path / "tests").mkdir()
    (tmp_path / "examples").mkdir()

    with patch("osa_tool.operations.codebase.organization.repo_organizer.logger") as mock_logger:
        # Act
        repo.add_directories()

        # Assert
        assert any("already exists" in str(c.args[0]) for c in mock_logger.info.call_args_list)


@pytest.mark.parametrize(
    "filename,patterns,expected",
    [
        ("test_something.py", RepoOrganizer.TEST_PATTERNS, True),
        ("something_test.py", RepoOrganizer.TEST_PATTERNS, True),
        ("normal.py", RepoOrganizer.TEST_PATTERNS, False),
        ("example_script.py", RepoOrganizer.EXAMPLE_PATTERNS, True),
        ("sample_run.py", RepoOrganizer.EXAMPLE_PATTERNS, True),
        ("unrelated.py", RepoOrganizer.EXAMPLE_PATTERNS, False),
    ],
)
def test_match_patterns(mock_config_manager, filename, patterns, expected, tmp_path):
    """
    Tests whether a given filename matches any of the provided patterns.
    
    This is a parameterized test that validates the behavior of `RepoOrganizer.match_patterns` using predefined test and example patterns from the `RepoOrganizer` class. The test ensures the pattern matching works correctly for both positive and negative cases.
    
    Args:
        mock_config_manager: A mocked configuration manager used to initialize the `RepoOrganizer` instance.
        filename: The name of the file to test against the patterns.
        patterns: A list of glob-like patterns (e.g., `RepoOrganizer.TEST_PATTERNS` or `RepoOrganizer.EXAMPLE_PATTERNS`) to match the filename against.
        expected: The expected boolean result (`True` if the filename should match any pattern, `False` otherwise).
        tmp_path: A temporary directory path fixture provided by pytest, used to isolate the test by setting the repository's working path.
    
    Why:
        The test uses a temporary directory to avoid interference with the actual filesystem and to ensure the `RepoOrganizer` instance operates in a clean, isolated environment. The `_fix_paths` helper is called to update the repository's internal directory paths (like `tests_dir` and `examples_dir`) to point to subdirectories within the temporary path, ensuring the pattern matching logic can locate the correct folders if needed.
    
    Returns:
        None
    """
    # Act
    repo = RepoOrganizer(mock_config_manager)
    repo.repo_path = str(tmp_path)
    _fix_paths(repo, tmp_path)

    # Assert
    assert repo.match_patterns(filename, patterns) is expected


def test_move_files_by_patterns_moves_files(mock_config_manager, tmp_path):
    """
    Tests that `move_files_by_patterns` correctly moves matching files.
    
    This test creates a temporary repository structure, places a test file at the
    root matching the test patterns, and verifies that the method moves the file
    to the designated tests directory while logging the action.
    
    WHY: This test validates the core file-moving functionality of the repository organizer, ensuring that files matching specified patterns are relocated to the correct target directory and that appropriate logging occurs, which is essential for maintaining a well-structured repository.
    
    Args:
        mock_config_manager: A mocked configuration manager for the repository.
        tmp_path: A temporary directory path fixture for test isolation.
    """
    # Arrange
    repo = RepoOrganizer(mock_config_manager)
    repo.repo_path = str(tmp_path)
    _fix_paths(repo, tmp_path)
    repo.add_directories()

    # Create a test file at repo root
    test_file = tmp_path / "test_abc.py"
    test_file.write_text("print('hi')")

    with patch("osa_tool.operations.codebase.organization.repo_organizer.logger") as mock_logger:
        # Act
        repo.move_files_by_patterns(repo.tests_dir, RepoOrganizer.TEST_PATTERNS)

    # Assert
    moved_file = tmp_path / "tests" / "test_abc.py"
    assert moved_file.exists()
    assert not test_file.exists()
    assert any("Moved" in str(c.args[0]) for c in mock_logger.info.call_args_list)


def test_move_files_by_patterns_skips_already_in_target(mock_config_manager, tmp_path):
    """
    Tests that `move_files_by_patterns` skips moving files already located in the target directory.
    
    WHY: This ensures the method avoids unnecessary file operations and prevents errors by not moving files that are already in their intended destination.
    
    Args:
        mock_config_manager: A mocked configuration manager object.
        tmp_path: A temporary path fixture for test file system operations.
    
    Returns:
        None.
    """
    # Arrange
    repo = RepoOrganizer(mock_config_manager)
    repo.repo_path = str(tmp_path)
    _fix_paths(repo, tmp_path)
    repo.add_directories()

    inside_test_file = tmp_path / "tests" / "test_inside.py"
    inside_test_file.write_text("print('inside')")

    with patch("osa_tool.operations.codebase.organization.repo_organizer.shutil.move") as mock_move:
        # Act
        repo.move_files_by_patterns(repo.tests_dir, RepoOrganizer.TEST_PATTERNS)

        # Assert
        mock_move.assert_not_called()


def test_move_files_handles_exception(mock_config_manager, tmp_path):
    """
    Tests that the move_files_by_patterns method handles exceptions gracefully.
    
    This test verifies that when an OSError (e.g., a disk error) occurs during file movement,
    the operation logs an appropriate error message and leaves the source file in place.
    
    Args:
        mock_config_manager: A mocked configuration manager object.
        tmp_path: A temporary directory path for test setup.
    
    Returns:
        None.
    """
    # Arrange
    repo = RepoOrganizer(mock_config_manager)
    repo.repo_path = str(tmp_path)
    _fix_paths(repo, tmp_path)
    repo.add_directories()

    test_file = tmp_path / "test_err.py"
    test_file.write_text("print('oops')")

    with (
        patch(
            "osa_tool.operations.codebase.organization.repo_organizer.shutil.move", side_effect=OSError("disk error")
        ),
        patch("osa_tool.operations.codebase.organization.repo_organizer.logger") as mock_logger,
    ):
        # Act
        repo.move_files_by_patterns(repo.tests_dir, RepoOrganizer.TEST_PATTERNS)

    # Assert
    assert test_file.exists()
    assert any("Failed to move" in str(c.args[0]) for c in mock_logger.error.call_args_list)


def test_organize_runs_all(mock_config_manager, tmp_path):
    """
    Tests the `organize` method of `RepoOrganizer` to ensure it moves all relevant files.
    
    This test verifies that when `organize` is called, it correctly moves test files
    to the tests directory and example files to the examples directory, and logs a
    completion message.
    
    WHY: This test ensures the core file organization functionality works as intended in a temporary, isolated environment, confirming that the correct directories are created and files are moved to their designated locations.
    
    Args:
        mock_config_manager: A mocked configuration manager object for the repository organizer.
        tmp_path: A temporary directory path provided by pytest for test file operations.
    
    Returns:
        None
    """
    # Arrange
    repo = RepoOrganizer(mock_config_manager)
    repo.repo_path = str(tmp_path)
    _fix_paths(repo, tmp_path)

    (tmp_path / "test_func.py").write_text("test")
    (tmp_path / "demo_script.py").write_text("demo")

    with patch("osa_tool.operations.codebase.organization.repo_organizer.logger") as mock_logger:
        # Act
        repo.organize()

    # Assert
    assert (tmp_path / "tests" / "test_func.py").exists()
    assert (tmp_path / "examples" / "demo_script.py").exists()
    assert any("completed" in str(c.args[0]) for c in mock_logger.info.call_args_list)


@pytest.mark.parametrize(
    "excluded_dir",
    [".git", ".venv", "__pycache__", "node_modules", ".idea", ".vscode"],
)
def test_move_files_skips_each_excluded_dir(mock_config_manager, tmp_path, excluded_dir):
    """
    Tests that files inside each excluded directory are skipped during move operation.
    
    WHY: This ensures that common development and system directories (like version control, virtual environments, caches, and IDE settings) are not processed or moved, preventing accidental modification of tool‑specific files and keeping the repository organization focused on source code.
    
    Args:
        mock_config_manager: Fixture providing a mock configuration manager.
        tmp_path: Fixture providing a temporary directory path.
        excluded_dir: The name of the excluded directory to test. The test runs for each of the following values: ".git", ".venv", "__pycache__", "node_modules", ".idea", ".vscode".
    
    Returns:
        None.
    """
    # Arrange
    repo = RepoOrganizer(mock_config_manager)
    repo.repo_path = str(tmp_path)
    _fix_paths(repo, tmp_path)
    repo.add_directories()

    dpath = tmp_path / excluded_dir
    dpath.mkdir()
    (dpath / "test_excluded.py").write_text("print('skip me')")

    with patch("osa_tool.operations.codebase.organization.repo_organizer.shutil.move") as mock_move:
        # Act
        repo.move_files_by_patterns(repo.tests_dir, RepoOrganizer.TEST_PATTERNS)

    # Assert
    assert (dpath / "test_excluded.py").exists()
    mock_move.assert_not_called()
