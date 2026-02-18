import pytest
from unittest.mock import mock_open, patch


@patch("builtins.open", new_callable=mock_open, read_data="import os\nos.path.join('test')")
@patch("os.path.exists", return_value=False)
def test_update_code(mock_open, translator):
    """
    Test that the translator updates a file with translated content.
    
    Parameters
    ----------
    mock_open : mock
        Mocked open function used to verify that the file is opened for writing.
    translator : object
        The translator instance whose `update_code` method is being tested.
    
    Returns
    -------
    None
    """
    # Act
    translator.update_code("/repo/file.py", {"test": "translated_test"})
    # Assert
    mock_open.assert_called_with("/repo/file.py", "w", encoding="utf-8")


@patch("builtins.open", new_callable=mock_open, read_data="import os")
def test_update_code_with_invalid_regex(mock_open, translator):
    """
    Test that the translator's `update_code` method does not attempt to write to a file
    when supplied with a translation mapping that contains an invalid regular expression.
    
    Args:
        mock_open: A mocked version of the built-in `open` function, provided by the
            `@patch` decorator. It simulates file I/O for the test.
        translator: The instance of the translator class under test, which provides
            the `update_code` method.
    
    Returns:
        None
    """
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
    """
    Test the update_code method of the translator.
    
    This test verifies that the translator correctly updates import statements and
    path references in a source file according to a provided rename map. It uses
    pytest parametrize to run multiple scenarios and a mocked open to capture
    file writes.
    
    Parameters
    ----------
    mock_open : mock
        Mocked built-in open function used to simulate file reading and writing.
    translator : object
        Instance of the translator class under test, which provides an
        update_code method.
    rename_map : dict
        Mapping of original identifiers to their new names that should be
        applied during the update.
    input_code : str
        The original source code content that will be read from the file.
    expected_output : str
        The expected source code after the translator has applied the rename
        map.
    
    Returns
    -------
    None
        This function does not return a value; it asserts that the file was
        written with the expected transformed content.
    """
    # Arrange
    mock_open.return_value.read.return_value = input_code
    # Act
    translator.update_code("/repo/file.py", rename_map)
    # Assert
    mock_open.assert_called_with("/repo/file.py", "w", encoding="utf-8")
    mock_open().write.assert_called_with(expected_output)
