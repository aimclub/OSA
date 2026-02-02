from pathlib import Path

from osa_tool.tools.repository_analysis.dependencies import DependencyExtractor
from osa_tool.tools.repository_analysis.documentation import DocumentationAnalyzer
from osa_tool.tools.repository_analysis.models import RepositoryData
from osa_tool.tools.repository_analysis.testing import TestAnalyzer
from osa_tool.utils.utils import get_repo_tree


class RepositoryAnalyzer:
    def __init__(self, repo_path: str, existing_jobs: set[str]):
        self.repo_path = repo_path
        self.existing_jobs = list(existing_jobs)
        self.tree = get_repo_tree(repo_path)

    def analyze(self) -> RepositoryData:
        # Dependency analysis
        dep_extractor = DependencyExtractor(self.tree, self.repo_path)
        dependencies_list = list(dep_extractor.extract_techs())
        dependencies = {"python": dependencies_list}
        python_version = dep_extractor.extract_python_version_requirement()

        # Workflow analysis
        workflows = self.existing_jobs

        # Documentation analysis
        doc_analyzer = DocumentationAnalyzer(self.repo_path, self.tree)
        documentation = doc_analyzer.analyze()

        # Test analysis
        test_analyzer = TestAnalyzer(self.tree, dependencies_list, self.existing_jobs)
        testing = test_analyzer.analyze()

        # Basic stats
        total_files, total_loc = self._count_files_and_lines()

        return RepositoryData(
            dependencies=dependencies,
            python_version=python_version,
            workflows=workflows,
            documentation=documentation,
            testing=testing,
            total_py_files=total_files,
            total_loc=total_loc,
            repo_tree=self.tree,
        )

    def _count_files_and_lines(self):
        total_files, total_loc = 0, 0
        for f in Path(self.repo_path).rglob("*.py"):
            if f.is_file():
                total_files += 1
                try:
                    total_loc += len(f.read_text(encoding="utf-8", errors="ignore").splitlines())
                except Exception:
                    pass
        return total_files, total_loc
