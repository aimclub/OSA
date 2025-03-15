import os
import nbformat
from nbconvert import PythonExporter
import logging
import ast
import re
from rich.logging import RichHandler

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

logger = logging.getLogger("rich")


class NotebookConverter:
    """Class for converting Jupyter notebooks (.ipynb) to Python scripts."""

    def __init__(self, figures_dir: str = "figures") -> None:
        self.exporter = PythonExporter()
        self.figures_dir = figures_dir

    def process_path(self, path: str) -> None:
        """Processes the specified notebook file or directory.

        Args:
            path: The path to the notebook or directory containing notebooks.
        """
        if os.path.isdir(path):
            self.convert_notebooks_in_directory(path)
        elif os.path.isfile(path) and path.endswith(".ipynb"):
            self.convert_notebook(path)
        else:
            logger.error("Invalid path or unsupported file type: %s", path)

    def convert_notebooks_in_directory(self, directory: str) -> None:
        """Converts all .ipynb files in the specified directory.

        Args:
            directory: The path to the directory containing notebooks.
        """
        for dirpath, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith(".ipynb"):
                    notebook_path = os.path.join(dirpath, filename)
                    self.convert_notebook(notebook_path)

    def convert_notebook(self, notebook_path: str) -> None:
        """Converts a single notebook file to a Python script.

        Args:
            notebook_path: The path to the notebook file to be converted.
        """
        try:
            with open(notebook_path, 'r') as f:
                notebook_content = nbformat.read(f, as_version=4)

            (body, _) = self.exporter.from_notebook_node(notebook_content)

            body = self.process_visualizations(body)
            
            if self.is_syntax_correct(body):
                script_name = os.path.splitext(notebook_path)[0] + '.py'
                with open(script_name, 'w') as script_file:
                    script_file.write(body)
                logger.info("Converted notebook to script: %s", script_name)
            else:
                logger.error("Converted notebook has invalid syntax: %s", notebook_path)

        except Exception as e:
            logger.error("Failed to convert notebook %s: %s", notebook_path, repr(e))

    def process_visualizations(self, code: str) -> str:
        """Change code for visualizations.

        Args:
            code: The Python code as a string.

        Returns:
            The modified code without printing visualizations and tables.
        """
        init_code = (
            f"import os\n"
            f"os.makedirs('{self.figures_dir}', exist_ok=True)\n"
            f"figure_counter = 0\n\n"
        )

        pattern = r'''(?mix)
            ^\s*
            (
                \w+\.(info|head|tail|describe)\(.*\)
                | \w+\s*$
                | display\(.*\)
                | \#\s*In\[.*?\]\s*:?
            )
        '''

        code = re.sub(pattern, '', code)
        code = re.sub(r'\n\s*\n', '\n', code)
        
        def replacement(match):
            indent = match.group(1)
            return (
                f"{indent}global figure_counter"
                f"{indent}plt.savefig(os.path.join('{self.figures_dir}', f'figure_{{figure_counter}}.png'))"
                f"{indent}figure_counter += 1"
                f"{indent}plt.close()"
            )

        code = re.sub(
            r'(\s*)(plt|sns)\.show\(\)',
            replacement,
            code
        )

        return init_code + code
    
    def is_syntax_correct(self, code: str) -> bool:
        """Checks if the given code has valid syntax.

        Args:
            code: The Python code as a string.

        Returns:
            True if the syntax is correct, False otherwise.
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False
