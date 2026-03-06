from pathlib import Path
from unittest.mock import patch, Mock, mock_open, call

import pytest

from osa_tool.operations.codebase.directory_translation.dirs_and_files_translator import RepositoryStructureTranslator
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


def test_init_sets_attributes(mock_config_manager):
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
    # Arrange
    translator = RepositoryStructureTranslator(mock_config_manager)

    # Assert
    for name in translator.excluded_names:
        assert translator._translate_text(name) == name


def test_translate_text_calls_model_handler(mock_config_manager):
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
