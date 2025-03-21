import pytest
import nbformat
import logging
from unittest.mock import patch
from osa_tool.convertion.notebook_converter import NotebookConverter

logger = logging.getLogger("rich")

@pytest.fixture
def converter():
    return NotebookConverter()

@pytest.fixture
def sample_notebook():
    return nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell("plt.show()"),
            nbformat.v4.new_code_cell("df.head()"),
            nbformat.v4.new_code_cell("display(data)")
        ]
    )

def test_process_path_with_directory(tmpdir, converter):
    test_dir = tmpdir.mkdir("test_dir")
    test_file = test_dir.join("test.ipynb")
    test_file.write("content")
    
    with patch.object(converter, "convert_notebooks_in_directory") as mock_convert:
        converter.process_path(str(test_dir))
        mock_convert.assert_called_once_with(str(test_dir))

def test_process_path_with_file(tmpdir, converter):
    test_file = tmpdir.join("test.ipynb")
    test_file.write("content")
    
    with patch.object(converter, "convert_notebook") as mock_convert:
        converter.process_path(str(test_file))
        mock_convert.assert_called_once_with(str(test_file))

def test_convert_notebook_success(tmpdir, converter, sample_notebook):
    test_file = tmpdir.join("test.ipynb")
    nbformat.write(sample_notebook, test_file)
    
    with patch("builtins.open"), \
         patch("nbformat.read") as mock_read, \
         patch("ast.parse"):
        
        mock_read.return_value = sample_notebook
        converter.convert_notebook(str(test_file))
        logger.info.assert_called()

@pytest.mark.parametrize("input_code,expected", [
    (
        "plt.show()",
        "import os\nos.makedirs('test_figures', exist_ok=True)\n\nplt.savefig(os.path.join('test_figures', 'figure_line2.png'))\nplt.close()\n"
    ),

    (
        "    plt.show()",
        "import os\nos.makedirs('test_figures', exist_ok=True)\n\n    plt.savefig(os.path.join('test_figures', 'figure_line2.png'))\n    plt.close()\n"
    )
])
def test_process_visualizations(converter, input_code, expected):
    processed = converter.process_visualizations("test", input_code)
    assert processed.strip() == expected.strip()

def test_syntax_check_valid(converter):
    assert converter.is_syntax_correct("print('Hello World')") is True

def test_syntax_check_invalid(converter):
    assert converter.is_syntax_correct("print('Hello World'") is False
