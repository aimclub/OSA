import os
from unittest.mock import mock_open, patch

import nbformat
import pytest

from osa_tool.operations.codebase.notebook_conversion.notebook_converter import NotebookConverter


def test_is_syntax_correct(mock_config_manager):
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
    # Arrange
    converter = NotebookConverter(mock_config_manager)
    with patch.object(converter, "_convert_directory") as mock_dir:
        with patch("os.path.isdir", return_value=True):
            # Act
            converter._process_path("some_dir")

            # Assert
            mock_dir.assert_called_once_with("some_dir")


def test_process_path_single_file(mock_config_manager):
    # Arrange
    converter = NotebookConverter(mock_config_manager)
    with patch.object(converter, "_convert_single") as mock_nb:
        with patch("os.path.isdir", return_value=False), patch("os.path.isfile", return_value=True):
            # Act
            converter._process_path("file.ipynb")

            # Assert
            mock_nb.assert_called_once_with("file.ipynb")


def test_convert_notebooks_in_directory_calls_convert_notebook(mock_config_manager):
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
