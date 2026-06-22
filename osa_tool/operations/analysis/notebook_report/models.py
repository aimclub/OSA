from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class NotebookIssue:
    slug: str
    description: str
    recommendation: str
    details: str | None = None


@dataclass
class NotebookStatistics:
    number_of_cells: int = 0
    number_of_markdown_cells: int = 0
    number_of_code_cells: int = 0
    number_of_raw_cells: int = 0
    number_of_functions: int | None = None
    number_of_classes: int | None = None
    number_of_markdown_lines: int = 0
    number_of_markdown_titles: int = 0
    number_of_empty_code_cells: int = 0
    number_of_non_executed_code_cells: int = 0


@dataclass
class NotebookAnalysisResult:
    path: str
    relative_path: str
    statistics: NotebookStatistics
    issues: list[NotebookIssue] = field(default_factory=list)
    analysis_errors: list[str] = field(default_factory=list)

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def has_errors(self) -> bool:
        return bool(self.analysis_errors)


@dataclass
class NotebookAnalysisSummary:
    total_notebooks: int = 0
    analyzed_notebooks: int = 0
    failed_notebooks: int = 0
    notebooks_with_issues: int = 0
    total_issues: int = 0
    invalid_syntax_notebooks: int = 0
    non_executed_notebooks: int = 0
    issue_frequencies: dict[str, int] = field(default_factory=dict)


@dataclass
class NotebookAnalysisBundle:
    summary: NotebookAnalysisSummary
    notebooks: list[NotebookAnalysisResult]
