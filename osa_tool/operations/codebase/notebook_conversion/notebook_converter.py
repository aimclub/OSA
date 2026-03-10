import ast
import os
import re

import nbformat
from nbconvert import PythonExporter

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class NotebookConverter:
    """
    Class for converting Jupyter notebooks (.ipynb) to Python scripts.

    During the conversion process, lines of code that display visualizations are replaced
    with lines that save them to folders. Additionally, the code for outputting table contents
    and their descriptions is removed.

    The resulting script is saved after ensuring that there are no syntax errors.
    """

    def __init__(self, config_manager: ConfigManager, notebook_paths: list[str] | None = None) -> None:
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.notebook_paths = notebook_paths or []
        self.exporter = PythonExporter()

        self.events: list[OperationEvent] = []

    def convert_notebooks(self) -> dict:
        """Converts Jupyter notebooks to Python scripts based on provided paths."""
        try:
            if len(self.notebook_paths) == 0:
                self._process_path(self.repo_path)
            else:
                for path in self.notebook_paths:
                    self._process_path(path)
            return {"result": "Notebook conversion completed", "events": self.events}
        except Exception as e:
            logger.error("Error while converting notebooks: %s", repr(e), exc_info=True)
            self._emit(EventKind.FAILED, "notebooks", {"error": repr(e)})
            return {"result": None, "events": self.events}

    def _process_path(self, path: str) -> None:
        """Processes the specified notebook file or directory.

        Args:
            path: The path to the notebook or directory containing notebooks.
        """
        if os.path.isdir(path):
            self._convert_directory(path)
            return
        if os.path.isfile(path) and path.endswith(".ipynb"):
            self._convert_single(path)
            return
        logger.error("Invalid path or unsupported file type: %s", path)
        self._emit(EventKind.SKIPPED, path)

    def _convert_directory(self, directory: str) -> None:
        """Converts all .ipynb files in the specified directory.

        Args:
            directory: The path to the directory containing notebooks.
        """
        for dirpath, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith(".ipynb"):
                    self._convert_single(os.path.join(dirpath, filename))

    def _convert_single(self, notebook_path: str) -> None:
        """Converts a single notebook file to a Python script.

        Args:
            notebook_path: The path to the notebook file to be converted.
        """
        try:
            with open(notebook_path, "r") as f:
                nb_node = nbformat.read(f, as_version=4)

            self._emit(EventKind.ANALYZED, notebook_path)

            body, _ = self.exporter.from_notebook_node(nb_node)
            self._emit(EventKind.GENERATED, notebook_path, {"source": "notebook_export"})

            notebook_name = os.path.splitext(os.path.basename(notebook_path))[0]
            body = self._process_code(notebook_name, body)
            self._emit(EventKind.REFINED, notebook_path)

            if not self._is_syntax_correct(body):
                logger.error("Converted notebook has invalid syntax: %s", notebook_path)
                self._emit(EventKind.SKIPPED, notebook_path, {"reason": "invalid syntax"})
                return

            script_path = os.path.splitext(notebook_path)[0] + ".py"
            with open(script_path, "w") as script_file:
                script_file.write(body)

            self._emit(EventKind.WRITTEN, script_path)

        except Exception as e:
            logger.error("Failed to convert notebook %s: %s", notebook_path, repr(e))
            self._emit(EventKind.FAILED, notebook_path, {"error": repr(e)})

    @staticmethod
    def _process_code(figures_dir: str, code: str) -> str:
        """Modify visualization code & remove noise."""
        init_code = "import os\n" f"os.makedirs('{figures_dir}_figures', exist_ok=True)\n\n"

        # Detect if visualizations exist → prepend init
        pattern_show = r"(\s*)(plt|sns)\.show\(\)"
        if re.search(pattern_show, code):
            code = init_code + code

        def repl_show(match):
            indent = match.group(1)
            return (
                f"{indent}plt.savefig(os.path.join('{figures_dir}_figures', f'figure.png'))\n" f"{indent}plt.close()\n"
            )

        code = re.sub(pattern_show, repl_show, code)

        pattern_2 = r"""(?mix)
            ^\s*
            (
                \w+\.(info|head|tail|describe)\(.*\)
                | (?!continue$)(?!break$)\w+\s*$
                | display\(.*\)
                | \#\s*In\[.*?\]\s*:?
                | (?:!|%)?pip\s+install\s+[^\n]+
            )
        """
        code = re.sub(pattern_2, "", code, flags=re.MULTILINE)
        code = re.sub(r"\n\s*\n", "\n", code)

        # Different file names for each figure call
        pattern_fig = r"figure\.png"
        lines = code.split("\n")
        for i, line in enumerate(lines):
            lines[i] = re.sub(pattern_fig, f"figure_line{i+1}.png", line)
        code = "\n".join(lines)

        pattern_4 = re.compile(
            r"""(?x)
            ^(\s*(if|elif|else)[^\n]*:\n)
            (
                (?:\s* \#.*\n
                | \s*\n
                )+
            )
            """,
            re.MULTILINE,
        )

        while re.search(pattern_4, code):
            code = re.sub(pattern_4, "", code)

        return code

    @staticmethod
    def _is_syntax_correct(code: str) -> bool:
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

    def _emit(self, kind: EventKind, target: str, data: dict | None = None):
        event = OperationEvent(kind=kind, target=target, data=data or {})
        self.events.append(event)
