from unittest.mock import patch

import pytest

from osa_tool.tools.repository_analysis.sourcerank import SourceRank


@pytest.fixture
def sourcerank_with_repo_tree(mock_config_manager, mock_parse_folder_name):
    """Factory fixture to create SourceRank instance with given repo_tree"""

    def factory(repo_tree):
        with (
            patch("osa_tool.analytics.sourcerank.get_repo_tree", return_value=repo_tree),
            patch("osa_tool.analytics.sourcerank.parse_folder_name", return_value=mock_parse_folder_name),
        ):
            return SourceRank(mock_config_manager)

    return factory
