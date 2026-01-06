from dataclasses import dataclass
from typing import Dict, Optional, List, Any


@dataclass
class RepositoryData:
    """
    Combined results of repo_analysis.
    Used by the Planner to understand repository state without reading full context.
    """

    # From DependencyExtractor
    dependencies: Dict[str, List[str]] | None = None
    python_version: Optional[str] = None

    # From WorkflowManager
    workflows: List[str] | None = None

    # From DocumentationAnalyzer
    documentation: Dict[str, Any] | None = None

    # From TestAnalyzer
    testing: Dict[str, Any] | None = None

    # General
    total_py_files: Optional[int] = None
    total_loc: Optional[int] = None
    repo_tree: Optional[str] = None
