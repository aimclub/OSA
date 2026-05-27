import pytest

from tests.utils.mocks.repo_trees import get_mock_repo_tree

METHOD_CASES = {
    "readme_presence": [("FULL", True), ("MINIMAL", False)],
    "license_presence": [("FULL", True), ("MINIMAL", False), ("LICENSE_ONLY", True)],
    "examples_presence": [("FULL", True), ("WITH_EXAMPLES_ONLY", True), ("MINIMAL", False)],
    "docs_presence": [("FULL", True), ("WITH_DOCS", True), ("MINIMAL", False)],
    "tests_presence": [("FULL", True), ("WITH_TESTS", True), ("MINIMAL", False)],
    "citation_presence": [("FULL", True), ("WITH_CITATION_ONLY", True), ("MINIMAL", False)],
    "contributing_presence": [("FULL", True), ("WITH_CONTRIBUTING_ONLY", True), ("MINIMAL", False)],
    "requirements_presence": [("FULL", True), ("WITH_REQUIREMENTS_ONLY", True), ("MINIMAL", False)],
}


@pytest.mark.parametrize(
    "method_name, repo_tree_type, expected",
    [(method, tree_type, expected) for method, cases in METHOD_CASES.items() for tree_type, expected in cases],
)
def test_source_rank_methods(method_name, repo_tree_type, expected, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree(repo_tree_type)
    instance = sourcerank_with_repo_tree(repo_tree_data)

    # Act
    method = getattr(instance, method_name)
    result = method()

    # Assert
    assert result is expected, f"{method_name} failed for tree: {repo_tree_type}"
