import os
from unittest.mock import patch


@patch("os.rename")
def test_rename_files(mock_rename, translator):
    # Act
    with (
        patch.object(translator, "_get_all_files", return_value=["/repo/file.txt"]),
        patch.object(
            translator,
            "translate_files",
            return_value=({"/repo/file.txt": "/repo/new_file.txt"}, {}),
        ),
    ):
        translator.rename_files()
    expected_call = tuple(
        os.path.normpath(path) for path in ("/repo/file.txt", "/repo/new_file.txt")
    )
    result_call = tuple(os.path.normpath(path) for path in mock_rename.call_args[0])
    # Assert
    assert result_call == expected_call


@patch("os.rename")
def test_rename_directories(mock_rename, translator):
    # Act
    with (
        patch.object(
            translator, "_get_all_directories", return_value=["/repo/old_dir"]
        ),
        patch.object(
            translator, "translate_directories", return_value={"old_dir": "new_dir"}
        ),
    ):
        translator.rename_directories()
    expected_call = tuple(
        os.path.normpath(path) for path in ("/repo/old_dir", "/repo/new_dir")
    )
    result_call = tuple(os.path.normpath(path) for path in mock_rename.call_args[0])
    # Assert
    assert result_call == expected_call
