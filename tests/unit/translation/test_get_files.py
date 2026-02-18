import os
from unittest.mock import patch


@patch("os.walk")
def test_get_python_files(mock_walk, mock_walk_data, translator):
    """
    Test that the translator's private method `_get_python_files` correctly
    collects all Python files from a mocked directory tree.
    
    Parameters
    ----------
    mock_walk : mock
        Mock object for `os.walk` used to simulate the file system traversal.
    mock_walk_data : list
        The data that `mock_walk` should return, representing the directory
        structure to be walked.
    translator : object
        Instance of the class under test, which provides the `_get_python_files`
        method.
    
    Returns
    -------
    None
        This test function performs an assertion and does not return a value.
    """
    # Arrane
    mock_walk.return_value = mock_walk_data
    # Act
    result = [os.path.normpath(path) for path in translator._get_python_files()]
    expected = [
        os.path.normpath("/repo/file.py"),
        os.path.normpath("/repo/subdir/module.py"),
    ]
    # Assert
    assert result == expected


@patch("os.walk")
def test_get_all_files(mock_walk, mock_walk_data, translator):
    """
    Test that the translator's private method `_get_all_files` correctly retrieves all files.
    
    Parameters
    ----------
    mock_walk : MagicMock
        The patched `os.walk` function used to simulate filesystem traversal.
    mock_walk_data : list
        The data that `mock_walk` should return, representing directory structure.
    translator : object
        An instance of the translator class whose `_get_all_files` method is being tested.
    
    Returns
    -------
    None
        This function does not return a value; it asserts that the method under test behaves as expected.
    """
    # Arrange
    mock_walk.return_value = mock_walk_data
    # Act
    result = translator._get_all_files()
    # Assert
    assert len(result) == 4


@patch("os.walk")
def test_get_all_directories(mock_walk, mock_walk_data, translator):
    """
    test_get_all_directories
    
    Tests that the translator's internal method `_get_all_directories` correctly
    returns all directories discovered by `os.walk`. The test patches
    `os.walk` to provide a controlled set of directory data, invokes the
    translator method, normalizes the resulting paths, and asserts that the
    output matches the expected list of directories.
    
    Args:
        mock_walk: The patched `os.walk` function used to supply mock directory
            traversal data.
        mock_walk_data: The data that `mock_walk` should return, representing
            the directory structure to be processed.
        translator: The instance of the class under test that contains the
            `_get_all_directories` method.
    
    Returns:
        None
    """
    # Arrange
    mock_walk.return_value = mock_walk_data
    # Act
    result = [os.path.normpath(path) for path in translator._get_all_directories()]
    expected = [os.path.normpath("/repo/subdir"), os.path.normpath("/repo/subdir2")]
    # Assert
    assert result == expected
