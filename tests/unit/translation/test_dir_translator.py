import pytest
from unittest.mock import mock_open, patch


@patch(
    "builtins.open", new_callable=mock_open, read_data="import os\nos.path.join('test')"
)
@patch("os.path.exists", return_value=False)
def test_update_code(mock_open, translator):
    # Act
    translator.update_code("/repo/file.py", {"test": "translated_test"})
    # Assert
    mock_open.assert_called_with("/repo/file.py", "w", encoding="utf-8")


@patch("builtins.open", new_callable=mock_open, read_data="import os")
def test_update_code_with_invalid_regex(mock_open, translator):
    # Arrange
    invalid_pattern = r"[a-zA-Z]+"
    translations = {invalid_pattern: "translated_text"}
    # Act
    translator.update_code("/repo/file.py", translations)
    # Assert
    mock_open().write.assert_not_called()


@pytest.mark.parametrize(
    "rename_map, input_code, expected_output",
    [
        (
            {"os": "new_os", "sys": "new_sys"},
            "import os\nimport sys\nfrom os.path import join",
            "import new_os\nimport new_sys\nfrom new_os.path import join",
        ),
        (
            {"folder": "new_folder", "file": "new_file"},
            "os.path.join('folder', 'file')\nPath('folder/file')",
            "os.path.join('new_folder', 'new_file')\nPath('new_folder/new_file')",
        ),
        (
            {"folder": "new_folder"},
            "shutil.copy('folder/file', 'folder/destination')",
            "shutil.copy('new_folder/file', 'new_folder/destination')",
        ),
        (
            {"folder": "new_folder"},
            "glob.glob('folder/*.py')",
            "glob.glob('new_folder/*.py')",
        ),
    ],
)
@patch("builtins.open", new_callable=mock_open)
def test_update_code(mock_open, translator, rename_map, input_code, expected_output):
    # Arrange
    mock_open.return_value.read.return_value = input_code
    # Act
    translator.update_code("/repo/file.py", rename_map)
    # Assert
    mock_open.assert_called_with("/repo/file.py", "w", encoding="utf-8")
    mock_open().write.assert_called_with(expected_output)
