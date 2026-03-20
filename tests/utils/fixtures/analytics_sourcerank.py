from unittest.mock import patch

import pytest

from osa_tool.tools.repository_analysis.sourcerank import SourceRank


@pytest.fixture
def sourcerank_with_repo_tree(mock_config_manager, mock_parse_folder_name):
    """
    Factory fixture to create a SourceRank instance with a specified repository tree structure.
    
    This fixture enables isolated testing of SourceRank by allowing the injection of a mock
    repository tree. It patches the `get_repo_tree` function to return the provided `repo_tree`
    and ensures `parse_folder_name` uses a predefined mock. This setup is useful for unit tests
    that require a controlled repository structure without interacting with the actual filesystem
    or Git operations.
    
    Args:
        mock_config_manager: A mocked configuration manager passed to the SourceRank constructor.
        mock_parse_folder_name: A mocked return value for the `parse_folder_name` function.
    
    Returns:
        A factory function that, when called with a `repo_tree` argument, returns a SourceRank
        instance configured with the provided repository tree and the mocked dependencies.
    """

    def factory(repo_tree):
        with (
            patch("osa_tool.tools.repository_analysis.sourcerank.get_repo_tree", return_value=repo_tree),
            patch(
                "osa_tool.tools.repository_analysis.sourcerank.parse_folder_name", return_value=mock_parse_folder_name
            ),
        ):
            return SourceRank(mock_config_manager)

    return factory
