import os
from unittest.mock import patch, mock_open

import nbformat
import pytest

from osa_tool.convertion.notebook_converter import NotebookConverter  # change to your actual module import


def test_is_syntax_correct():
    # Arrange
    converter = NotebookConverter()

    # Assert
    assert converter.is_syntax_correct("x = 1")
    assert not converter.is_syntax_correct("x ==")


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
def test_process_code_transformations(input_code, expected_parts, unexpected_parts):
    # Arrange
    converter = NotebookConverter()

    # Act
    output = converter.process_code("test_dir", input_code)

    # Assert
    for part in expected_parts:
        assert part in output
    for part in unexpected_parts:
        assert part not in output


def test_process_path_directory():
    # Arrange
    converter = NotebookConverter()
    with patch.object(converter, "convert_notebooks_in_directory") as mock_dir:
        with patch("os.path.isdir", return_value=True):
            # Act
            converter.process_path("some_dir")

            # Assert
            mock_dir.assert_called_once_with("some_dir")


def test_process_path_single_file():
    # Arrange
    converter = NotebookConverter()
    with patch.object(converter, "convert_notebook") as mock_nb:
        with patch("os.path.isdir", return_value=False), patch("os.path.isfile", return_value=True):
            # Act
            converter.process_path("file.ipynb")

            # Assert
            mock_nb.assert_called_once_with("file.ipynb")


def test_convert_notebooks_in_directory_calls_convert_notebook():
    # Arrange
    converter = NotebookConverter()
    with (
        patch("os.walk", return_value=[("root", [], ["file.ipynb", "skip.txt"])]),
        patch.object(converter, "convert_notebook") as mock_nb,
    ):
        # Act
        converter.convert_notebooks_in_directory("some_dir")
        # Assert
        mock_nb.assert_called_once_with(os.path.join("root", "file.ipynb"))


def test_convert_notebook_success():
    # Arrange
    converter = NotebookConverter()
    fake_notebook = nbformat.v4.new_notebook()
    exporter_output = ("print('hello')", None)

    with (
        patch("builtins.open", mock_open(read_data="{}")),
        patch("nbformat.read", return_value=fake_notebook),
        patch.object(converter.exporter, "from_notebook_node", return_value=exporter_output),
        patch.object(converter, "process_code", return_value="print('ok')"),
        patch.object(converter, "is_syntax_correct", return_value=True),
        patch("os.path.splitext", side_effect=os.path.splitext),
        patch("builtins.open", mock_open()) as mock_file,
    ):
        # Act
        converter.convert_notebook("test.ipynb")

        # Assert
        mock_file().write.assert_called_once_with("print('ok')")


def test_convert_notebook_syntax_error():
    # Arrange
    converter = NotebookConverter()
    fake_notebook = nbformat.v4.new_notebook()
    exporter_output = ("print('bad')", None)

    with (
        patch("builtins.open", mock_open(read_data="{}")),
        patch("nbformat.read", return_value=fake_notebook),
        patch.object(converter.exporter, "from_notebook_node", return_value=exporter_output),
        patch.object(converter, "is_syntax_correct", return_value=False),
    ):
        converter.convert_notebook("bad.ipynb")
