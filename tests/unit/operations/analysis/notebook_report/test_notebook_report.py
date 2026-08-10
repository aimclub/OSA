from pathlib import Path
from unittest.mock import MagicMock

import nbformat
import pytest

from osa_tool.operations.analysis.notebook_report.analyzer import NotebookReportAnalyzer
from osa_tool.operations.analysis.notebook_report.report_maker import NotebookReportGenerator
from osa_tool.utils.utils import parse_folder_name


def _write_notebook(path: Path, cells: list) -> None:
    notebook = nbformat.v4.new_notebook(cells=cells)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        nbformat.write(notebook, file)


@pytest.fixture
def notebook_repo(tmp_path, mock_config_manager):
    repo_dir = tmp_path / parse_folder_name(str(mock_config_manager.config.git.repository))
    repo_dir.mkdir()

    _write_notebook(
        repo_dir / "good.ipynb",
        [
            nbformat.v4.new_markdown_cell("# Analysis"),
            nbformat.v4.new_markdown_cell("Notebook introduction."),
            nbformat.v4.new_code_cell("import math\nvalue = math.sqrt(4)", execution_count=1),
            nbformat.v4.new_markdown_cell("Notebook conclusion."),
        ],
    )
    _write_notebook(
        repo_dir / "bad-Copy1.ipynb",
        [
            nbformat.v4.new_code_cell("def broken(:\n    pass", execution_count=None),
            nbformat.v4.new_code_cell("import os", execution_count=None),
        ],
    )
    return repo_dir


def test_notebook_report_analyzer_keeps_processing_after_notebook_issues(
    tmp_path, monkeypatch, mock_config_manager, notebook_repo
):
    monkeypatch.chdir(tmp_path)
    analyzer = NotebookReportAnalyzer(mock_config_manager)

    bundle = analyzer.analyze()

    assert bundle.summary.total_notebooks == 2
    assert bundle.summary.analyzed_notebooks == 2
    assert bundle.summary.total_issues >= 1
    assert any(result.relative_path == "good.ipynb" for result in bundle.notebooks)
    bad_result = next(result for result in bundle.notebooks if result.relative_path == "bad-Copy1.ipynb")
    assert any(issue.slug == "invalid-python-syntax" for issue in bad_result.issues)
    assert any(issue.slug == "duplicate-notebook-not-renamed" for issue in bad_result.issues)


def test_notebook_report_analyzer_filters_specific_paths(tmp_path, monkeypatch, mock_config_manager, notebook_repo):
    monkeypatch.chdir(tmp_path)
    analyzer = NotebookReportAnalyzer(mock_config_manager, ["good.ipynb"])

    bundle = analyzer.analyze()

    assert bundle.summary.total_notebooks == 1
    assert bundle.notebooks[0].relative_path == "good.ipynb"


def test_notebook_report_analyzer_uses_resolved_clone_directory(tmp_path, mock_config_manager):
    repo_dir = tmp_path / "external-local-repository"
    repo_dir.mkdir()
    _write_notebook(repo_dir / "local.ipynb", [nbformat.v4.new_markdown_cell("# Local")])

    analyzer = NotebookReportAnalyzer(mock_config_manager, repo_path=str(repo_dir))

    bundle = analyzer.analyze()

    assert [result.relative_path for result in bundle.notebooks] == ["local.ipynb"]


def test_non_python_notebook_skips_python_specific_checks(tmp_path, mock_config_manager):
    notebook_path = tmp_path / "analysis.R.ipynb"
    notebook = nbformat.v4.new_notebook(
        cells=[nbformat.v4.new_code_cell("library(ggplot2)\nx <- 1", execution_count=1)],
        metadata={"kernelspec": {"language": "R", "name": "ir", "display_name": "R"}},
    )
    with notebook_path.open("w", encoding="utf-8") as file:
        nbformat.write(notebook, file)

    result = NotebookReportAnalyzer(mock_config_manager, [str(notebook_path)]).analyze().notebooks[0]

    assert result.statistics.number_of_functions is None
    assert not any(issue.slug == "invalid-python-syntax" for issue in result.issues)


def test_export_failure_is_reported_as_analysis_error(tmp_path, mock_config_manager, monkeypatch):
    notebook_path = tmp_path / "export.ipynb"
    _write_notebook(notebook_path, [nbformat.v4.new_code_cell("x = 1", execution_count=1)])
    analyzer = NotebookReportAnalyzer(mock_config_manager, [str(notebook_path)])
    monkeypatch.setattr(analyzer.exporter, "from_notebook_node", MagicMock(side_effect=RuntimeError("export failed")))

    bundle = analyzer.analyze()

    assert bundle.summary.failed_notebooks == 1
    assert bundle.summary.analyzed_notebooks == 0
    assert "Failed to export notebook to Python" in bundle.notebooks[0].analysis_errors[0]


def test_unexpected_notebook_failure_does_not_stop_remaining_analysis(tmp_path, mock_config_manager, monkeypatch):
    broken_path = tmp_path / "broken.ipynb"
    healthy_path = tmp_path / "healthy.ipynb"
    _write_notebook(broken_path, [nbformat.v4.new_code_cell("x = 1", execution_count=1)])
    _write_notebook(healthy_path, [nbformat.v4.new_code_cell("y = 1", execution_count=1)])
    analyzer = NotebookReportAnalyzer(mock_config_manager, [str(broken_path), str(healthy_path)])
    original = analyzer._analyze_single

    def analyze_with_one_failure(path):
        if path == str(broken_path):
            raise TypeError("malformed metadata")
        return original(path)

    monkeypatch.setattr(analyzer, "_analyze_single", analyze_with_one_failure)

    bundle = analyzer.analyze()

    assert bundle.summary.total_notebooks == 2
    assert bundle.summary.failed_notebooks == 1
    assert any(result.path == str(healthy_path) and not result.has_errors for result in bundle.notebooks)


def test_counts_async_functions_and_comment_blocks_after_code(tmp_path, mock_config_manager):
    notebook_path = tmp_path / "async.ipynb"
    _write_notebook(
        notebook_path,
        [
            nbformat.v4.new_code_cell(
                "value = 1\n# one\n# two\n# three\n# four\nasync def run():\n    return value",
                execution_count=1,
            )
        ],
    )

    result = NotebookReportAnalyzer(mock_config_manager, [str(notebook_path)]).analyze().notebooks[0]

    assert result.statistics.number_of_functions == 1
    assert any(issue.slug == "long-multiline-python-comment" for issue in result.issues)


def test_notebook_report_analyzer_uses_single_issue_for_fully_non_executed_notebook(
    tmp_path, monkeypatch, mock_config_manager
):
    repo_dir = tmp_path / parse_folder_name(str(mock_config_manager.config.git.repository))
    repo_dir.mkdir()
    _write_notebook(
        repo_dir / "stale.ipynb",
        [
            nbformat.v4.new_markdown_cell("# Stale notebook"),
            nbformat.v4.new_code_cell("x = 1", execution_count=None),
            nbformat.v4.new_code_cell("y = x + 1", execution_count=None),
        ],
    )

    monkeypatch.chdir(tmp_path)
    analyzer = NotebookReportAnalyzer(mock_config_manager)

    bundle = analyzer.analyze()

    result = next(result for result in bundle.notebooks if result.relative_path == "stale.ipynb")
    issue_slugs = {issue.slug for issue in result.issues}

    assert "non-executed-notebook" in issue_slugs
    assert "non-executed-cells" not in issue_slugs


def test_notebook_report_generator_builds_pdf(tmp_path, monkeypatch, mock_config_manager, mock_repository_metadata):
    repo_dir = tmp_path / parse_folder_name(str(mock_config_manager.config.git.repository))
    repo_dir.mkdir()
    _write_notebook(
        repo_dir / "report.ipynb",
        [
            nbformat.v4.new_markdown_cell("# Report"),
            nbformat.v4.new_markdown_cell("Intro"),
            nbformat.v4.new_code_cell("x = 1", execution_count=1),
            nbformat.v4.new_markdown_cell("Summary"),
        ],
    )

    git_agent = MagicMock()
    git_agent.metadata = mock_repository_metadata
    git_agent.clone_dir = str(repo_dir)

    monkeypatch.chdir(tmp_path)
    generator = NotebookReportGenerator(mock_config_manager, git_agent, False)

    result = generator.run()

    output_path = Path(generator.output_path)
    assert result["result"]["report"] == generator.filename
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_notebook_report_pdf_build_failure_is_returned_as_failed_event(
    tmp_path, monkeypatch, mock_config_manager, mock_repository_metadata
):
    repo_dir = tmp_path / parse_folder_name(str(mock_config_manager.config.git.repository))
    repo_dir.mkdir()
    git_agent = MagicMock()
    git_agent.metadata = mock_repository_metadata
    git_agent.clone_dir = str(repo_dir)
    generator = NotebookReportGenerator(mock_config_manager, git_agent, False)
    monkeypatch.setattr(generator, "build_pdf", MagicMock(side_effect=RuntimeError("disk is read-only")))

    result = generator.run()

    assert result["result"] == {"error": "disk is read-only"}
    assert result["events"][-1].kind.value == "failed"
