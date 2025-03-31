import pytest
import nbformat
from unittest.mock import patch, mock_open

from osa_tool.convertion.notebook_converter import NotebookConverter


@pytest.fixture
def converter():
    return NotebookConverter()


def create_test_notebook():
    nb = nbformat.v4.new_notebook()
    nb.cells.append(nbformat.v4.new_code_cell("""
import matplotlib.pyplot as plt
import pandas as pd

df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
df.head()

plt.plot([1, 2, 3], [4, 5, 6])
plt.show()
"""))
    return nb


@pytest.fixture
def tmp_notebook(tmp_path):
    nb = create_test_notebook()
    notebook_path = tmp_path / "test_notebook.ipynb"
    with open(notebook_path, "w", encoding="utf-8") as f:
        nbformat.write(nb, f)
    return notebook_path


@patch.object(NotebookConverter, "convert_notebooks_in_directory")
def test_process_path_with_directory(mock_convert, tmpdir, converter):
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
    # Arrange
    test_file = tmpdir.join("test.ipynb")
    test_file.write("content")
    # Act
    converter.process_path(str(test_file))
    # Assert
    mock_convert.assert_called_once_with(str(test_file))


def test_convert_notebook_success(tmp_notebook):
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
    # Arrange
    converter = NotebookConverter()
    # Act
    with patch("builtins.open", mock_open(read_data="invalid")):
        converter.convert_notebook("invalid.ipynb")
        # Assert
        mock_logger.assert_called_with("Failed to convert notebook %s: %s", "invalid.ipynb", mock_logger.call_args[0][2])


@pytest.mark.parametrize("input_code,expected", [
    (
        "plt.show()",
        "import os\nos.makedirs('test_figures', exist_ok=True)\nplt.savefig(os.path.join('test_figures', f'figure_line3.png'))\nplt.close()\n"
    ),

    (
        "    plt.show()",
        "import os\nos.makedirs('test_figures', exist_ok=True)\n    plt.savefig(os.path.join('test_figures', f'figure_line3.png'))\n    plt.close()\n"
    )
])
def test_process_visualizations(converter, input_code, expected):
    # Act
    processed = converter.process_visualizations("test", input_code)
    # Assert
    assert processed.strip() == expected.strip()


def test_syntax_check_valid(converter):
    # Assert
    assert converter.is_syntax_correct("print('Hello World')") is True


def test_syntax_check_invalid(converter):
    # Assert
    assert converter.is_syntax_correct("print('Hello World'") is False
