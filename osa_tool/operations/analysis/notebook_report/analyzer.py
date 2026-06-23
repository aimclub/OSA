from __future__ import annotations

import ast
import os
import re
from collections import Counter

import nbformat
from nbconvert import PythonExporter

from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.operations.analysis.notebook_report.models import (
    NotebookAnalysisBundle,
    NotebookAnalysisResult,
    NotebookAnalysisSummary,
    NotebookIssue,
    NotebookStatistics,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name

_MAX_CELLS_IN_NOTEBOOK = 50
_MAX_LINES_IN_CODE_CELL = 30
_INITIAL_CELLS = 3
_FINAL_CELLS = 3
_MIN_MD_CODE_RATIO = 0.3
_MAX_MULTILINE_PYTHON_COMMENT = 4


class NotebookReportAnalyzer:
    """Analyze notebooks without aborting on per-notebook failures."""

    def __init__(self, config_manager: ConfigManager, notebook_paths: list[str] | None = None) -> None:
        self.repo_url = str(config_manager.get_git_settings().repository)
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.notebook_paths = notebook_paths or []
        self.exporter = PythonExporter()
        self.events: list[OperationEvent] = []

    def analyze(self) -> NotebookAnalysisBundle:
        notebook_files = self._collect_notebook_files()
        results: list[NotebookAnalysisResult] = []

        for notebook_path in notebook_files:
            result = self._analyze_single(notebook_path)
            results.append(result)

        summary = self._build_summary(results)
        return NotebookAnalysisBundle(summary=summary, notebooks=results)

    def _collect_notebook_files(self) -> list[str]:
        roots = self.notebook_paths or [self.repo_path]
        collected: set[str] = set()

        for raw_path in roots:
            resolved_path = self._resolve_input_path(raw_path)
            if resolved_path is None:
                logger.warning("Notebook report target not found: %s", raw_path)
                self.events.append(
                    OperationEvent(kind=EventKind.SKIPPED, target=raw_path, data={"reason": "path not found"})
                )
                continue

            if os.path.isdir(resolved_path):
                for dirpath, dirnames, filenames in os.walk(resolved_path):
                    dirnames[:] = [d for d in dirnames if d != ".ipynb_checkpoints"]
                    for filename in filenames:
                        if filename.endswith(".ipynb"):
                            collected.add(os.path.abspath(os.path.join(dirpath, filename)))
            elif resolved_path.endswith(".ipynb"):
                collected.add(os.path.abspath(resolved_path))
            else:
                self.events.append(
                    OperationEvent(kind=EventKind.SKIPPED, target=resolved_path, data={"reason": "not a notebook"})
                )

        return sorted(collected)

    def _resolve_input_path(self, raw_path: str) -> str | None:
        candidates = []
        if os.path.isabs(raw_path):
            candidates.append(raw_path)
        else:
            candidates.extend(
                [
                    os.path.join(self.repo_path, raw_path),
                    os.path.join(os.getcwd(), raw_path),
                ]
            )

        for candidate in candidates:
            if os.path.exists(candidate):
                return os.path.abspath(candidate)
        return None

    def _analyze_single(self, notebook_path: str) -> NotebookAnalysisResult:
        relative_path = self._relative_path(notebook_path)
        self.events.append(OperationEvent(kind=EventKind.ANALYZED, target=relative_path))

        try:
            with open(notebook_path, "r", encoding="utf-8") as file:
                notebook = nbformat.read(file, as_version=4)
        except Exception as exc:
            logger.error("Failed to read notebook %s: %s", notebook_path, exc)
            self.events.append(OperationEvent(kind=EventKind.FAILED, target=relative_path, data={"error": repr(exc)}))
            return NotebookAnalysisResult(
                path=notebook_path,
                relative_path=relative_path,
                statistics=NotebookStatistics(),
                analysis_errors=[f"Failed to read notebook: {exc}"],
            )

        cells = list(notebook.cells)
        code_cells = [cell for cell in cells if cell.get("cell_type") == "code"]
        markdown_cells = [cell for cell in cells if cell.get("cell_type") == "markdown"]
        raw_cells = [cell for cell in cells if cell.get("cell_type") == "raw"]

        exported_script = self._export_notebook(notebook, relative_path)
        ast_tree = None
        has_invalid_python_syntax = False
        if exported_script is not None:
            try:
                ast_tree = ast.parse(exported_script)
            except SyntaxError:
                has_invalid_python_syntax = True

        stats = NotebookStatistics(
            number_of_cells=len(cells),
            number_of_markdown_cells=len(markdown_cells),
            number_of_code_cells=len(code_cells),
            number_of_raw_cells=len(raw_cells),
            number_of_functions=self._count_defs(ast_tree, ast.FunctionDef),
            number_of_classes=self._count_defs(ast_tree, ast.ClassDef),
            number_of_markdown_lines=sum(len(str(cell.get("source", "")).splitlines()) for cell in markdown_cells),
            number_of_markdown_titles=self._count_markdown_titles(markdown_cells),
            number_of_empty_code_cells=sum(1 for cell in code_cells if self._is_empty_code_cell(cell)),
            number_of_non_executed_code_cells=sum(1 for cell in code_cells if self._is_non_executed_code_cell(cell)),
        )

        issues: list[NotebookIssue] = []
        issue = self._filename_issues(relative_path)
        issues.extend(issue)

        if self._non_linear_execution(code_cells):
            issues.append(
                NotebookIssue(
                    slug="non-linear-execution",
                    description="Notebook cells were executed in a non-linear order.",
                    recommendation="Re-run the notebook from top to bottom to keep execution reproducible.",
                )
            )
        if stats.number_of_cells > _MAX_CELLS_IN_NOTEBOOK:
            issues.append(
                NotebookIssue(
                    slug="notebook-too-long",
                    description=f"Notebook contains more than {_MAX_CELLS_IN_NOTEBOOK} cells.",
                    recommendation="Split the notebook into smaller focused notebooks.",
                    details=f"Detected {stats.number_of_cells} cells.",
                )
            )
        if self._imports_beyond_first_code_cell(code_cells):
            issues.append(
                NotebookIssue(
                    slug="imports-beyond-first-cell",
                    description="Import statements were found beyond the first code cell.",
                    recommendation="Move imports to the first code cell to make dependencies explicit.",
                )
            )
        if self._missing_h1_heading(cells):
            issues.append(
                NotebookIssue(
                    slug="missing-h1-heading",
                    description="Initial cells do not contain an H1 markdown heading.",
                    recommendation="Add an H1 heading near the top of the notebook to explain its purpose.",
                )
            )
        if self._missing_opening_markdown(cells):
            issues.append(
                NotebookIssue(
                    slug="missing-opening-markdown",
                    description="Initial notebook cells do not contain descriptive markdown text.",
                    recommendation="Add introductory markdown explaining the goal and context of the notebook.",
                )
            )
        if self._missing_closing_markdown(cells):
            issues.append(
                NotebookIssue(
                    slug="missing-closing-markdown",
                    description="Final notebook cells do not contain descriptive markdown text.",
                    recommendation="Add concluding markdown summarizing results or next steps.",
                )
            )
        if self._too_few_markdown_cells(stats):
            ratio = 0.0
            if stats.number_of_code_cells:
                ratio = stats.number_of_markdown_cells / stats.number_of_code_cells
            issues.append(
                NotebookIssue(
                    slug="too-few-markdown-cells",
                    description="Notebook contains too few markdown cells relative to code cells.",
                    recommendation="Add more markdown to document the workflow and findings.",
                    details=f"Markdown/code ratio is {ratio:.2f}.",
                )
            )
        if has_invalid_python_syntax:
            issues.append(
                NotebookIssue(
                    slug="invalid-python-syntax",
                    description="Notebook contains invalid Python syntax in exported code.",
                    recommendation="Fix syntax errors so the notebook can be executed and converted safely.",
                )
            )
        is_fully_non_executed = self._is_non_executed_notebook(code_cells)
        if is_fully_non_executed:
            issues.append(
                NotebookIssue(
                    slug="non-executed-notebook",
                    description="All code cells appear to be non-executed.",
                    recommendation="Execute the notebook before committing it.",
                )
            )
        if stats.number_of_non_executed_code_cells and not is_fully_non_executed:
            issues.append(
                NotebookIssue(
                    slug="non-executed-cells",
                    description="Notebook contains non-executed code cells.",
                    recommendation="Execute remaining code cells or remove stale cells.",
                    details=f"{stats.number_of_non_executed_code_cells} code cell(s) are non-executed.",
                )
            )
        if stats.number_of_empty_code_cells:
            issues.append(
                NotebookIssue(
                    slug="empty-cells",
                    description="Notebook contains empty code cells.",
                    recommendation="Delete unused empty code cells to keep the notebook tidy.",
                    details=f"{stats.number_of_empty_code_cells} empty code cell(s) detected.",
                )
            )

        long_comment_cells = self._count_long_multiline_comment_cells(code_cells)
        if long_comment_cells:
            issues.append(
                NotebookIssue(
                    slug="long-multiline-python-comment",
                    description="Notebook contains long multiline Python comments inside code cells.",
                    recommendation="Prefer markdown cells over long inline comments in code cells.",
                    details=f"{long_comment_cells} code cell(s) contain long comment blocks.",
                )
            )

        long_code_cells = self._count_long_code_cells(code_cells)
        if long_code_cells:
            issues.append(
                NotebookIssue(
                    slug="cell-too-long",
                    description="Notebook contains long code cells.",
                    recommendation="Move larger code blocks into modules and keep notebooks focused on experiments.",
                    details=f"{long_code_cells} code cell(s) exceed {_MAX_LINES_IN_CODE_CELL} lines.",
                )
            )

        self.events.append(OperationEvent(kind=EventKind.REFINED, target=relative_path, data={"issues": len(issues)}))
        return NotebookAnalysisResult(
            path=notebook_path,
            relative_path=relative_path,
            statistics=stats,
            issues=issues,
        )

    def _export_notebook(self, notebook, relative_path: str) -> str | None:
        try:
            body, _ = self.exporter.from_notebook_node(notebook)
            return body
        except Exception as exc:
            logger.warning("Failed to export notebook %s to Python: %s", relative_path, exc)
            self.events.append(
                OperationEvent(kind=EventKind.SKIPPED, target=relative_path, data={"reason": "export failed"})
            )
            return None

    def _build_summary(self, results: list[NotebookAnalysisResult]) -> NotebookAnalysisSummary:
        issue_counter = Counter()
        invalid_syntax = 0
        non_executed_notebooks = 0

        for result in results:
            for issue in result.issues:
                issue_counter[issue.slug] += 1
            if any(issue.slug == "invalid-python-syntax" for issue in result.issues):
                invalid_syntax += 1
            if any(issue.slug == "non-executed-notebook" for issue in result.issues):
                non_executed_notebooks += 1

        return NotebookAnalysisSummary(
            total_notebooks=len(results),
            analyzed_notebooks=sum(1 for result in results if not result.has_errors),
            failed_notebooks=sum(1 for result in results if result.has_errors),
            notebooks_with_issues=sum(1 for result in results if result.issue_count > 0),
            total_issues=sum(result.issue_count for result in results),
            invalid_syntax_notebooks=invalid_syntax,
            non_executed_notebooks=non_executed_notebooks,
            issue_frequencies=dict(issue_counter.most_common()),
        )

    def _relative_path(self, path: str) -> str:
        try:
            return os.path.relpath(path, self.repo_path)
        except ValueError:
            return path

    @staticmethod
    def _count_defs(ast_tree: ast.AST | None, node_type: type[ast.AST]) -> int | None:
        if ast_tree is None:
            return None
        return sum(isinstance(node, node_type) for node in ast.walk(ast_tree))

    @staticmethod
    def _count_markdown_titles(markdown_cells: list) -> int:
        total = 0
        for cell in markdown_cells:
            for line in str(cell.get("source", "")).splitlines():
                if line.lstrip().startswith("#"):
                    total += 1
        return total

    @staticmethod
    def _is_empty_code_cell(cell) -> bool:
        return cell.get("execution_count") is None and not str(cell.get("source", "")).strip()

    @staticmethod
    def _is_non_executed_code_cell(cell) -> bool:
        return cell.get("execution_count") is None and bool(str(cell.get("source", "")).strip())

    @staticmethod
    def _non_linear_execution(code_cells: list) -> bool:
        execution_counts = [cell.get("execution_count") for cell in code_cells if cell.get("execution_count")]
        return execution_counts != sorted(execution_counts)

    @staticmethod
    def _imports_beyond_first_code_cell(code_cells: list) -> bool:
        for cell in code_cells[1:]:
            source = str(cell.get("source", ""))
            try:
                tree = ast.parse(source)
            except SyntaxError:
                continue
            if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in tree.body):
                return True
        return False

    @staticmethod
    def _is_heading_markdown(cell) -> bool:
        if cell.get("cell_type") != "markdown":
            return False
        pattern = re.compile(r"^\s*#{1,6}\s*[^#\n]*$")
        lines = [line for line in str(cell.get("source", "")).splitlines() if line and not line.isspace()]
        return bool(lines) and all(pattern.match(line) for line in lines)

    def _missing_h1_heading(self, cells: list) -> bool:
        pattern = re.compile(r"^\s*#\s*[^#\n]*$")
        initial_markdown = "\n".join(
            str(cell.get("source", "")) for cell in cells[:_INITIAL_CELLS] if cell.get("cell_type") == "markdown"
        )
        return not any(pattern.match(line) for line in initial_markdown.splitlines())

    def _missing_opening_markdown(self, cells: list) -> bool:
        return not any(
            cell.get("cell_type") == "markdown" and not self._is_heading_markdown(cell)
            for cell in cells[:_INITIAL_CELLS]
        )

    def _missing_closing_markdown(self, cells: list) -> bool:
        return not any(
            cell.get("cell_type") == "markdown" and not self._is_heading_markdown(cell)
            for cell in cells[-_FINAL_CELLS:]
        )

    @staticmethod
    def _too_few_markdown_cells(stats: NotebookStatistics) -> bool:
        if stats.number_of_code_cells == 0:
            return False
        return (stats.number_of_markdown_cells / stats.number_of_code_cells) < _MIN_MD_CODE_RATIO

    @staticmethod
    def _is_non_executed_notebook(code_cells: list) -> bool:
        return bool(code_cells) and all(
            cell.get("execution_count") is None and bool(str(cell.get("source", "")).strip()) for cell in code_cells
        )

    @staticmethod
    def _count_long_multiline_comment_cells(code_cells: list) -> int:
        pattern = re.compile(rf"([^\S\r\n]*#.*\n*){{{_MAX_MULTILINE_PYTHON_COMMENT},}}")
        return sum(1 for cell in code_cells if pattern.match(str(cell.get("source", ""))))

    @staticmethod
    def _count_long_code_cells(code_cells: list) -> int:
        return sum(1 for cell in code_cells if len(str(cell.get("source", "")).splitlines()) > _MAX_LINES_IN_CODE_CELL)

    @staticmethod
    def _filename_issues(relative_path: str) -> list[NotebookIssue]:
        issues: list[NotebookIssue] = []
        filename = os.path.basename(relative_path)
        if re.match(r"Untitled\d*\.ipynb$", filename):
            issues.append(
                NotebookIssue(
                    slug="untitled-notebook",
                    description="Notebook still uses a default Untitled name.",
                    recommendation="Rename the notebook to a meaningful file name.",
                )
            )
        if not re.search(r"^[A-Za-z0-9_.-]+$", filename):
            issues.append(
                NotebookIssue(
                    slug="non-portable-chars-in-name",
                    description="Notebook filename contains non-portable characters.",
                    recommendation="Use only letters, digits, dots, underscores, and hyphens in notebook names.",
                )
            )
        if re.match(r".*-Copy\d+\.ipynb$", filename):
            issues.append(
                NotebookIssue(
                    slug="duplicate-notebook-not-renamed",
                    description="Notebook looks like a duplicate copy that was not renamed.",
                    recommendation="Rename duplicated notebooks to a meaningful name.",
                )
            )
        return issues
