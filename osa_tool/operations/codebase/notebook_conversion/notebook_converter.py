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
    A class that facilitates the transformation of Jupyter notebook files into executable Python scripts, extracting and structuring code cells while preserving logical flow and content.
    
        During the conversion process, lines of code that display visualizations are replaced
        with lines that save them to folders. Additionally, the code for outputting table contents
        and their descriptions is removed.
    
        The resulting script is saved after ensuring that there are no syntax errors.
    """


    def __init__(self, config_manager: ConfigManager, notebook_paths: list[str] | None = None) -> None:
        """
        Initializes the NotebookConverter with configuration and notebook paths.
        
        Args:
            config_manager: Configuration manager providing git settings. Used to retrieve the repository URL.
            notebook_paths: Optional list of notebook file paths to process. If not provided, defaults to an empty list.
        
        Initializes the following instance attributes:
            repo_url (str): The URL of the Git repository, obtained from the configuration manager.
            repo_path (str): The local file system path where the repository is located. Constructed by joining the current working directory with a folder name parsed from the repository URL.
            notebook_paths (list[str]): List of notebook file paths to process.
            exporter (PythonExporter): Exporter for converting Jupyter notebooks to Python scripts.
            events (list[OperationEvent]): List to store operation events for logging or tracking during conversion processes.
        """
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.notebook_paths = notebook_paths or []
        self.exporter = PythonExporter()

        self.events: list[OperationEvent] = []

    def convert_notebooks(self) -> dict:
        """
        Converts Jupyter notebooks to Python scripts based on provided paths.
        
        This method orchestrates the conversion process by iterating over the notebook paths
        stored in the instance. If no specific paths are provided, it processes the entire
        repository directory. Each valid notebook is converted to a Python script, and the
        operation's progress and outcomes are tracked via events.
        
        Why:
        - It provides a unified entry point for batch conversion, handling both explicit file/directory lists and fallback to full repository processing.
        - Events are collected to enable detailed reporting, debugging, and auditing of the conversion steps, including successes and failures.
        
        Returns:
            A dictionary with two keys:
                - "result": A success message if conversion completes, or None if an error occurs.
                - "events": The list of OperationEvent instances recorded during the conversion, capturing all actions, skips, and errors.
        """
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
        """
        Processes the specified notebook file or directory.
        
        Why:
        This method serves as the entry point for conversion, determining whether the given path is a directory or a single notebook file and routing it to the appropriate handler. It ensures only valid .ipynb files or directories containing them are processed, logging errors and skipping invalid inputs.
        
        Args:
            path: The path to the notebook file or directory containing notebooks.
        
        Behavior:
            - If the path is a directory, calls `_convert_directory` to recursively convert all .ipynb files within it.
            - If the path is a single file with a .ipynb extension, calls `_convert_single` to convert that notebook.
            - If the path is neither a valid directory nor a .ipynb file, logs an error and emits a SKIPPED event for the path.
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
        """
        Converts all .ipynb files in the specified directory and its subdirectories.
        
        Why:
            This method enables batch processing of Jupyter notebooks by recursively traversing the directory tree, allowing the conversion of an entire project or folder structure at once.
        
        Args:
            directory: The path to the directory containing notebooks to be converted.
        
        Behavior:
            - Recursively walks through the given directory and all its subdirectories using os.walk.
            - For each file with a .ipynb extension, calls the internal _convert_single method to convert that notebook to a Python script.
            - Only files ending with .ipynb are processed; other files are ignored.
            - The conversion of each notebook is delegated to _convert_single, which handles reading, exporting, processing, and writing the output.
        """
        for dirpath, _, filenames in os.walk(directory):
            for filename in filenames:
                if filename.endswith(".ipynb"):
                    self._convert_single(os.path.join(dirpath, filename))

    def _convert_single(self, notebook_path: str) -> None:
        """
        Converts a single notebook file to a Python script.
        
        Args:
            notebook_path: The path to the notebook file to be converted.
        
        Why:
            This method handles the full conversion pipeline for one notebook: reading the notebook, exporting it to Python code, processing the code to remove notebook-specific artifacts and adapt visualizations, validating the syntax, and finally writing the resulting script to a file. Events are emitted at each step to track progress and errors.
        
        Behavior:
            - Reads the notebook file using nbformat.
            - Emits an ANALYZED event.
            - Exports the notebook to Python code using the class's exporter.
            - Emits a GENERATED event.
            - Processes the exported code to remove notebook noise and adapt visualization commands for standalone execution.
            - Emits a REFINED event.
            - Validates the processed code's syntax; if invalid, logs an error, emits a SKIPPED event, and stops conversion.
            - Writes the valid code to a .py file in the same directory as the original notebook.
            - Emits a WRITTEN event upon successful write.
            - If any exception occurs during the process, logs an error and emits a FAILED event with the error details.
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
        """
        Modify visualization code & remove noise from notebook cell code.
        
        This static method processes Python code extracted from notebook cells to prepare it for standalone script execution. It performs two main tasks: (1) adapting visualization commands to save figures to a specified directory instead of displaying them interactively, and (2) removing common notebook-specific statements and noise that are not needed in a pure Python script. This ensures the converted code runs cleanly outside a notebook environment and organizes generated figures systematically.
        
        Args:
            figures_dir: The base directory name where figures will be saved. A subdirectory named '{figures_dir}_figures' is created.
            code: The raw Python code string from a notebook cell to be processed.
        
        Returns:
            The processed code string with visualizations adapted and notebook-specific noise removed.
        
        Why:
            - plt.show() calls are replaced with plt.savefig() and plt.close() to save figures to disk instead of displaying them, which is necessary for non-interactive script execution.
            - Notebook-specific commands (e.g., display(), shell commands like pip install, cell markers like # In[ ]) are stripped because they are not valid in a standard Python script.
            - Redundant blank lines and empty conditional blocks (if/elif/else with only comments or whitespace) are cleaned up to produce cleaner, more readable output code.
            - Each figure is saved with a unique filename (figure_line{line_number}.png) to avoid overwriting when multiple figures are generated in the same script.
        """
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
        """
        Checks if the given Python code string has valid syntax by parsing it with `ast.parse`.
        
        Args:
            code: The Python code as a string.
        
        Returns:
            True if the syntax is correct, False otherwise.
        
        Why:
            This method is used to validate code snippets before further processing (e.g., in a notebook conversion pipeline) to avoid runtime errors from malformed syntax.
        """
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

    def _emit(self, kind: EventKind, target: str, data: dict | None = None):
        """
        Emit an operation event and store it in the events list.
        
        Args:
            kind: The type of event (e.g., conversion, validation, or error).
            target: The target of the event, typically a file path, object, or operation identifier.
            data: Optional dictionary containing additional event-specific details or metadata.
        
        Why:
            This method centralizes event logging within the conversion process, enabling tracking of operations, debugging, and later analysis of the conversion steps. Each event is stored as an OperationEvent instance in the class's events list for subsequent reporting or auditing.
        """
        event = OperationEvent(kind=kind, target=target, data=data or {})
        self.events.append(event)
