import os
from unittest.mock import patch


@patch("os.walk")
def test_get_python_files(mock_walk, mock_walk_data, translator):
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
    # Arrange
    mock_walk.return_value = mock_walk_data
    # Act
    result = translator._get_all_files()
    # Assert
    assert len(result) == 4


@patch("os.walk")
def test_get_all_directories(mock_walk, mock_walk_data, translator):
    # Arrange
    mock_walk.return_value = mock_walk_data
    # Act
    result = [os.path.normpath(path) for path in translator._get_all_directories()]
    expected = [
        os.path.normpath("/repo/subdir"),
        os.path.normpath("/repo/subdir2")
    ]
    # Assert
    assert result == expected
