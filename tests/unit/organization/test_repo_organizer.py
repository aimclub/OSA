from unittest.mock import patch

import pytest

from osa_tool.organization.repo_organizer import RepoOrganizer


def test_add_directories_creates_missing(tmp_path):
    # Arrange
    repo = RepoOrganizer(str(tmp_path))
    tests_dir = tmp_path / "tests"
    examples_dir = tmp_path / "examples"

    with patch("osa_tool.organization.repo_organizer.logger") as mock_logger:
        # Act
        repo.add_directories()

        # Assert
        assert tests_dir.exists()
        assert examples_dir.exists()
        assert any("Created directory" in str(c.args[0]) for c in mock_logger.info.call_args_list)


def test_add_directories_when_already_exist(tmp_path):
    # Arrange
    (tmp_path / "tests").mkdir()
    (tmp_path / "examples").mkdir()
    repo = RepoOrganizer(str(tmp_path))

    with patch("osa_tool.organization.repo_organizer.logger") as mock_logger:
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
def test_match_patterns(filename, patterns, expected, tmp_path):
    # Act
    repo = RepoOrganizer(str(tmp_path))

    # Assert
    assert repo.match_patterns(filename, patterns) is expected


def test_move_files_by_patterns_moves_files(tmp_path):
    # Arrange
    repo = RepoOrganizer(str(tmp_path))
    repo.add_directories()

    # Create a test file at repo root
    test_file = tmp_path / "test_abc.py"
    test_file.write_text("print('hi')")

    with patch("osa_tool.organization.repo_organizer.logger") as mock_logger:
        # Act
        repo.move_files_by_patterns(repo.tests_dir, RepoOrganizer.TEST_PATTERNS)

    # Assert
    moved_file = tmp_path / "tests" / "test_abc.py"
    assert moved_file.exists()
    assert not test_file.exists()
    assert any("Moved" in str(c.args[0]) for c in mock_logger.info.call_args_list)


def test_move_files_by_patterns_skips_already_in_target(tmp_path):
    # Arrange
    repo = RepoOrganizer(str(tmp_path))
    repo.add_directories()

    inside_test_file = tmp_path / "tests" / "test_inside.py"
    inside_test_file.write_text("print('inside')")

    with patch("osa_tool.organization.repo_organizer.shutil.move") as mock_move:
        # Act
        repo.move_files_by_patterns(repo.tests_dir, RepoOrganizer.TEST_PATTERNS)

        # Assert
        mock_move.assert_not_called()


def test_move_files_handles_exception(tmp_path):
    # Arrange
    repo = RepoOrganizer(str(tmp_path))
    repo.add_directories()

    test_file = tmp_path / "test_err.py"
    test_file.write_text("print('oops')")

    with (
        patch("osa_tool.organization.repo_organizer.shutil.move", side_effect=OSError("disk error")),
        patch("osa_tool.organization.repo_organizer.logger") as mock_logger,
    ):
        # Act
        repo.move_files_by_patterns(repo.tests_dir, RepoOrganizer.TEST_PATTERNS)

    # Assert
    assert test_file.exists()
    assert any("Failed to move" in str(c.args[0]) for c in mock_logger.error.call_args_list)


def test_organize_runs_all(tmp_path):
    # Arrange
    repo = RepoOrganizer(str(tmp_path))

    (tmp_path / "test_func.py").write_text("test")
    (tmp_path / "demo_script.py").write_text("demo")

    with patch("osa_tool.organization.repo_organizer.logger") as mock_logger:
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
def test_move_files_skips_each_excluded_dir(tmp_path, excluded_dir):
    # Arrange
    repo = RepoOrganizer(str(tmp_path))
    repo.add_directories()

    dpath = tmp_path / excluded_dir
    dpath.mkdir()
    (dpath / "test_excluded.py").write_text("print('skip me')")

    with patch("osa_tool.organization.repo_organizer.shutil.move") as mock_move:
        # Act
        repo.move_files_by_patterns(repo.tests_dir, RepoOrganizer.TEST_PATTERNS)

    # Assert
    assert (dpath / "test_excluded.py").exists()
    mock_move.assert_not_called()
