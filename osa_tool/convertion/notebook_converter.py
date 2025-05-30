import ast
import os
import re

import nbformat
from nbconvert import PythonExporter

from osa_tool.utils import logger


class NotebookConverter:
    """
    Class for converting Jupyter notebooks (.ipynb) to Python scripts.

    During the conversion process, lines of code that display visualizations are replaced
    with lines that save them to folders. Additionally, the code for outputting table contents
    and their descriptions is removed.

    The resulting script is saved after ensuring that there are no syntax errors.
    """

    def __init__(self) -> None:
        self.exporter = PythonExporter()

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
            with open(notebook_path, "r") as f:
                notebook_content = nbformat.read(f, as_version=4)

            (body, _) = self.exporter.from_notebook_node(notebook_content)

            notebook_name = os.path.splitext(os.path.basename(notebook_path))[0]
            body = self.process_visualizations(notebook_name, body)

            if self.is_syntax_correct(body):
                script_name = os.path.splitext(notebook_path)[0] + ".py"
                with open(script_name, "w") as script_file:
                    script_file.write(body)
                logger.info("Converted notebook to script: %s", script_name)
            else:
                logger.error("Converted notebook has invalid syntax: %s", notebook_path)

        except Exception as e:
            logger.error("Failed to convert notebook %s: %s", notebook_path, repr(e))

    @staticmethod
    def process_visualizations(figures_dir: str, code: str) -> str:
        """Change code for visualizations.

        Args:
            figures_dir: Path to save a figure
            code: The Python code as a string.

        Returns:
            The modified code without printing visualizations and tables.
        """
        init_code = (
            f"import os\n" f"os.makedirs('{figures_dir}_figures', exist_ok=True)\n\n"
        )

        pattern_1 = r"(\s*)(plt|sns)\.show\(\)"
        if re.search(pattern_1, code):
            code = init_code + code

        def replacement(match):
            indent = match.group(1)
            return (
                f"{indent}plt.savefig(os.path.join('{figures_dir}_figures', f'figure.png'))\n"
                f"{indent}plt.close()\n"
            )

        code = re.sub(pattern_1, replacement, code)

        pattern_2 = r"""(?mix)
            ^\s*
            (
                \w+\.(info|head|tail|describe)\(.*\)
                | \w+\s*$
                | display\(.*\)
                | \#\s*In\[.*?\]\s*:?
            )
        """
        code = re.sub(pattern_2, "", code, flags=re.MULTILINE)
        code = re.sub(r"\n\s*\n", "\n", code)

        pattern_3 = r"figure\.png"
        lines = code.split("\n")
        for i, line in enumerate(lines):
            lines[i] = re.sub(pattern_3, f"figure_line{i+1}.png", line)
        code = "\n".join(lines)

        return code

    @staticmethod
    def is_syntax_correct(code: str) -> bool:
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
