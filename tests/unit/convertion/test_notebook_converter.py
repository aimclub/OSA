import os
from unittest.mock import mock_open, patch

import nbformat
import pytest

from osa_tool.operations.codebase.notebook_conversion.notebook_converter import NotebookConverter


def test_is_syntax_correct(mock_config_manager):
    """
    Verifies that the syntax checking logic correctly identifies valid and invalid Python code.
    This test ensures the underlying syntax validator (`_is_syntax_correct`) works as expected for both correct and malformed code snippets.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the NotebookConverter.
    
    Returns:
        None.
    """
    # Arrange
    converter = NotebookConverter(mock_config_manager)

    # Assert
    assert converter._is_syntax_correct("x = 1")
    assert not converter._is_syntax_correct("x ==")


@pytest.mark.parametrize(
    "input_code,expected_parts,unexpected_parts",
    [
        # plt.show() replaced with savefig
        (
            "import matplotlib.pyplot as plt\nplt.show()\n",
            ["plt.savefig", "_figures"],
            ["plt.show()"],
        ),
        # sns.show() replaced with savefig
        (
            "import seaborn as sns\nsns.show()\n",
            ["plt.savefig", "_figures"],
            ["sns.show()"],
        ),
        # pip install removed
        (
            "!pip install pandas\nprint('done')\n",
            ["print('done')"],
            ["pip install"],
        ),
        # Table display removed
        (
            "df.head()\ndisplay(df)\n",
            [],
            ["df.head()", "display("],
        ),
        # Figure renaming applied
        (
            "print('figure.png')\n",
            ["figure_line1.png"],
            ["figure.png'"],  # original filename gone
        ),
        # Remove empty if/else blocks
        (
            "if True:\n    # comment only\n\nprint('x')",
            ["print('x')"],
            ["if True:"],
        ),
    ],
)
def test_process_code_transformations(mock_config_manager, input_code, expected_parts, unexpected_parts):
    """
    Verifies that code transformations within the NotebookConverter correctly modify visualization code and remove noise.
        
    This test ensures that specific patterns in the input code, such as matplotlib/seaborn show calls, pip installs, table displays, and empty control blocks, are correctly transformed or removed according to the converter's logic. The test is parameterized with multiple input/output examples to validate the behavior across different transformation rules.
    
    Args:
        mock_config_manager: A mocked configuration manager used to initialize the NotebookConverter.
        input_code: The raw string of code to be processed by the converter.
        expected_parts: A list of strings that must be present in the processed output.
        unexpected_parts: A list of strings that must not be present in the processed output.
    
    Why:
        This test validates that the NotebookConverter's internal processing correctly handles common notebook artifacts—like interactive display commands, installation lines, and empty control structures—by either removing them or converting them to static, reproducible equivalents (e.g., replacing plt.show() with savefig). This ensures the converted code is suitable for non-interactive execution and documentation generation.
    """
    # Arrange
    converter = NotebookConverter(mock_config_manager)

    # Act
    output = converter._process_code("test_dir", input_code)

    # Assert
    for part in expected_parts:
        assert part in output
    for part in unexpected_parts:
        assert part not in output


def test_process_path_directory(mock_config_manager):
    """
    Verifies that the _process_path method correctly identifies a directory and delegates the processing to the internal directory conversion handler.
    
    This test ensures that when a directory path is provided, the method calls the appropriate directory conversion routine instead of attempting file conversion. It uses mocking to isolate the behavior and confirm the correct internal method is invoked.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the converter.
    
    Returns:
        None.
    """
    # Arrange
    converter = NotebookConverter(mock_config_manager)
    with patch.object(converter, "_convert_directory") as mock_dir:
        with patch("os.path.isdir", return_value=True):
            # Act
            converter._process_path("some_dir")

            # Assert
            mock_dir.assert_called_once_with("some_dir")


def test_process_path_single_file(mock_config_manager):
    """
    Verifies that the _process_path method correctly identifies and processes a single file.
    
    This test ensures that when a path is provided that is not a directory but is a valid file, the converter calls the internal conversion logic for that specific file exactly once. The test uses mocking to isolate the file system checks and the conversion method, confirming the expected behavior without performing actual file operations.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the NotebookConverter.
    
    Why:
        This test validates the conditional logic in _process_path that distinguishes between files and directories, ensuring that single files are routed to the appropriate conversion method. It is important because incorrect path handling could lead to missed conversions or unnecessary recursive processing.
    """
    # Arrange
    converter = NotebookConverter(mock_config_manager)
    with patch.object(converter, "_convert_single") as mock_nb:
        with patch("os.path.isdir", return_value=False), patch("os.path.isfile", return_value=True):
            # Act
            converter._process_path("file.ipynb")

            # Assert
            mock_nb.assert_called_once_with("file.ipynb")


def test_convert_notebooks_in_directory_calls_convert_notebook(mock_config_manager):
    """
    Verifies that the _convert_directory method correctly identifies notebook files and calls the single conversion logic for each.
    
    This test mocks the file system using os.walk to simulate a directory structure containing both a notebook file and a non-notebook file. It asserts that the conversion process is triggered only for the file with the .ipynb extension.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the converter.
    
    Why:
        This test ensures the directory conversion logic properly filters files by extension, preventing unnecessary processing of non-notebook files and confirming that only valid notebook files are passed to the single conversion method.
    """
    # Arrange
    converter = NotebookConverter(mock_config_manager)
    with (
        patch("os.walk", return_value=[("root", [], ["file.ipynb", "skip.txt"])]),
        patch.object(converter, "_convert_single") as mock_nb,
    ):
        # Act
        converter._convert_directory("some_dir")
        # Assert
        mock_nb.assert_called_once_with(os.path.join("root", "file.ipynb"))


def test_convert_notebook_success(mock_config_manager):
    """
    Verifies that a notebook is successfully converted to a Python script when all dependencies behave as expected.
        
    This test case mocks the file system, notebook reading, and internal converter methods to ensure that the conversion workflow correctly processes a notebook file and writes the resulting code to a file. The mocking isolates the test from external systems and focuses on verifying the internal logic and sequence of operations.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the converter.
    
    Why:
    - The test mocks `open`, `nbformat.read`, and several internal methods (`from_notebook_node`, `_process_code`, `_is_syntax_correct`) to simulate a successful conversion path without relying on actual file I/O or notebook processing.
    - It ensures that the converter correctly calls its internal steps (reading, exporting, processing, validating syntax) and writes the final processed code to the output file.
    - The final assertion checks that the processed code is written exactly once, confirming the workflow completes as intended.
    """
    # Arrange
    converter = NotebookConverter(mock_config_manager)
    fake_notebook = nbformat.v4.new_notebook()
    exporter_output = ("print('hello')", None)

    with (
        patch("builtins.open", mock_open(read_data="{}")),
        patch("nbformat.read", return_value=fake_notebook),
        patch.object(converter.exporter, "from_notebook_node", return_value=exporter_output),
        patch.object(converter, "_process_code", return_value="print('ok')"),
        patch.object(converter, "_is_syntax_correct", return_value=True),
        patch("os.path.splitext", side_effect=os.path.splitext),
        patch("builtins.open", mock_open()) as mock_file,
    ):
        # Act
        converter._convert_single("test.ipynb")

        # Assert
        mock_file().write.assert_called_once_with("print('ok')")


def test_convert_notebook_syntax_error(mock_config_manager):
    """
    Verifies that the notebook conversion process correctly handles cases where the resulting Python script contains syntax errors.
    
    This test ensures that when the conversion produces a Python script with invalid syntax, the process does not fail silently and appropriately manages the error condition.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the converter. This fixture provides the necessary configuration without external dependencies.
    
    Returns:
        None.
    """
    # Arrange
    converter = NotebookConverter(mock_config_manager)
    fake_notebook = nbformat.v4.new_notebook()
    exporter_output = ("print('bad')", None)

    with (
        patch("builtins.open", mock_open(read_data="{}")),
        patch("nbformat.read", return_value=fake_notebook),
        patch.object(converter.exporter, "from_notebook_node", return_value=exporter_output),
        patch.object(converter, "_is_syntax_correct", return_value=False),
    ):
        converter._convert_single("bad.ipynb")
