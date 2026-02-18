from unittest.mock import patch, mock_open

import nbformat
import pytest

from osa_tool.convertion.notebook_converter import NotebookConverter


@pytest.fixture
def converter():
    """
    Creates and returns a NotebookConverter instance.
    
    Returns:
        NotebookConverter: A new instance of NotebookConverter.
    """
    return NotebookConverter()


def create_test_notebook():
    """
    Creates a simple Jupyter notebook containing a single code cell that demonstrates
    basic data manipulation with pandas and plotting with matplotlib.
    
    The notebook is constructed using the `nbformat` library and includes a code
    cell that:
      * imports `matplotlib.pyplot` and `pandas`;
      * creates a small DataFrame;
      * displays the first rows of the DataFrame;
      * plots a simple line chart and shows it.
    
    Args:
        None
    
    Returns:
        nbformat.NotebookNode: A new notebook object with one code cell ready to
        be executed. The cell contains example code for pandas and matplotlib.
    """
    nb = nbformat.v4.new_notebook()
    nb.cells.append(
        nbformat.v4.new_code_cell(
            """
import matplotlib.pyplot as plt
import pandas as pd

df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
df.head()

plt.plot([1, 2, 3], [4, 5, 6])
plt.show()
"""
        )
    )
    return nb


@pytest.fixture
def tmp_notebook(tmp_path):
    """
    Creates a temporary Jupyter notebook file in the specified directory and returns its path.
    
    Args:
        tmp_path: A pathlib.Path-like object representing the directory where the
            temporary notebook should be written.
    
    Returns:
        Path to the newly created notebook file.
    """
    nb = create_test_notebook()
    notebook_path = tmp_path / "test_notebook.ipynb"
    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    return notebook_path


@patch.object(NotebookConverter, "convert_notebooks_in_directory")
def test_process_path_with_directory(mock_convert, tmpdir, converter):
    """
    Test that `NotebookConverter.process_path` correctly delegates to
    `convert_notebooks_in_directory` when the supplied path is a directory.
    
    Parameters
    ----------
    mock_convert : MagicMock
        The patched `convert_notebooks_in_directory` method of
        `NotebookConverter`.  It records calls made by `process_path`.
    tmpdir : py.path.local
        Temporary directory fixture provided by pytest.  Used to create a
        test directory and a dummy notebook file.
    converter : NotebookConverter
        Instance of the converter under test.  The method under test is
        `process_path`.
    
    Returns
    -------
    None
        This is a test method; it does not return a value.
    """
    # Arrange
    test_dir = tmpdir.mkdir("test_dir")
    test_file = test_dir.join("test.ipynb")
    test_file.write("content")
    # Act
    converter.process_path(str(test_dir))
    # Assert
    mock_convert.assert_called_once_with(str(test_dir))


@patch.object(NotebookConverter, "convert_notebook")
def test_process_path_with_file(mock_convert, tmpdir, converter):
    """
    Test that `NotebookConverter.process_path` correctly delegates to `convert_notebook` when the
    provided path points to a notebook file.
    
    Parameters
    ----------
    mock_convert
        Mock object replacing `NotebookConverter.convert_notebook` to verify it is called.
    tmpdir
        Temporary directory fixture used to create a test notebook file.
    converter
        Instance of `NotebookConverter` whose `process_path` method is exercised.
    
    Returns
    -------
    None
    """
    # Arrange
    test_file = tmpdir.join("test.ipynb")
    test_file.write("content")
    # Act
    converter.process_path(str(test_file))
    # Assert
    mock_convert.assert_called_once_with(str(test_file))


def test_convert_notebook_success(tmp_notebook):
    """
    Test that NotebookConverter successfully converts a notebook to a Python script.
    
    Parameters
    ----------
    tmp_notebook : Path
        Temporary notebook file path used for testing.
    
    Returns
    -------
    None
    
    This test verifies that the NotebookConverter converts the notebook to a .py file,
    ensures the output file exists, and checks that the generated script does not
    contain 'plt.show()' but does contain 'plt.savefig(' and does not contain '.head()'.
    """
    # Arrange
    converter = NotebookConverter()
    converter.convert_notebook(str(tmp_notebook))

    script_path = tmp_notebook.with_suffix(".py")
    # Act
    with open(script_path, "r", encoding="utf-8") as f:
        script_content = f.read()
    # Assert
    assert script_path.exists()
    assert "plt.show()" not in script_content
    assert "plt.savefig(" in script_content
    assert ".head()" not in script_content


@patch("logging.Logger.error")
def test_convert_notebook_invalid(mock_logger):
    """
    Test that converting an invalid notebook triggers an error log.
    
    This test creates a `NotebookConverter` instance and attempts to convert a
    notebook file containing invalid data.  The built‑in `open` function is
    patched to return the string `"invalid"` so that the conversion fails.
    The test then verifies that the logger's `error` method was called with
    the expected message and that the exception message is included in the
    log arguments.
    
    Parameters
    ----------
    mock_logger : mock
        Mock object injected by the `@patch("logging.Logger.error")` decorator
        to capture calls to the logger's error method.
    
    Returns
    -------
    None
    """
    # Arrange
    converter = NotebookConverter()
    # Act
    with patch("builtins.open", mock_open(read_data="invalid")):
        converter.convert_notebook("invalid.ipynb")
        # Assert
        mock_logger.assert_called_with(
            "Failed to convert notebook %s: %s",
            "invalid.ipynb",
            mock_logger.call_args[0][2],
        )


def test_syntax_check_valid(converter):
    """
    Test that the converter correctly identifies syntactically valid Python code.
    
    Args:
        converter: An object that provides an `is_syntax_correct` method used to check
            the syntax of a Python code string.
    
    Returns:
        None
    """
    # Assert
    assert converter.is_syntax_correct("print('Hello World')") is True


def test_syntax_check_invalid(converter):
    """
    Test that the converter correctly identifies an invalid syntax string.
    
    Args:
        converter: The converter instance that provides the `is_syntax_correct` method.
    
    Returns:
        None
    
    Raises:
        AssertionError: If the syntax check does not return False for an invalid input.
    """
    # Assert
    assert converter.is_syntax_correct("print('Hello World'") is False
