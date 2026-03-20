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
    """
    Tests a SourceRank method with different repository tree configurations.
    
    This method is a parameterized test that verifies the behavior of various
    SourceRank methods against different mock repository tree structures. It
    instantiates a SourceRank object with a specific repository tree, calls the
    target method, and asserts the result matches the expected value.
    
    The test uses a factory fixture to create isolated SourceRank instances with
    mocked dependencies, ensuring tests do not rely on actual filesystem or Git
    operations. This allows controlled validation of each SourceRank method's
    logic against predefined repository structures.
    
    Args:
        method_name: Name of the SourceRank method to test.
        repo_tree_type: Type identifier for the mock repository tree to use.
            This key corresponds to a predefined mock structure returned by
            `get_mock_repo_tree`.
        expected: Expected return value from the method call.
        sourcerank_with_repo_tree: Factory fixture that creates SourceRank
            instances with the given repository tree. The fixture handles mocking
            of external dependencies to provide a controlled test environment.
    
    Returns:
        None. This is a test method that performs assertions.
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree(repo_tree_type)
    instance = sourcerank_with_repo_tree(repo_tree_data)

    # Act
    method = getattr(instance, method_name)
    result = method()

    # Assert
    assert result is expected, f"{method_name} failed for tree: {repo_tree_type}"
