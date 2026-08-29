from pathlib import Path
from unittest.mock import patch

import pytest

from osa_tool.tools.repository_analysis.sourcerank import SourceRank


@pytest.fixture
def sourcerank_with_repo_tree(mock_config_manager):
    """Factory fixture to create SourceRank instance with given repo_tree"""

    def factory(repo_tree):
        with (
            patch("osa_tool.tools.repository_analysis.sourcerank.get_repo_tree", return_value=repo_tree),
            patch("osa_tool.tools.repository_analysis.sourcerank.resolve_repo_path", return_value=Path("/tmp/repo")),
        ):
            return SourceRank(mock_config_manager)

    return factory
