import pytest


@pytest.mark.parametrize(
    "tree, expected",
    [("README.md", True), ("readme.txt", True), ("docs/guide.pdf", False)],
)
def test_readme_presence(source_rank, tree, expected):
    """
    Test that the `readme_presence` method correctly identifies the presence of a README file.
    
    This test assigns a file path to the `tree` attribute of a `source_rank` instance and asserts that
    `source_rank.readme_presence()` returns the expected boolean value. The test is parameterized
    to run with multiple file names, verifying that the method treats files named `README.md` or
    `readme.txt` as present and other files as absent.
    
    Parameters
    ----------
    source_rank
        The object under test, expected to have a `tree` attribute and a `readme_presence` method.
    tree
        A string representing a file path to be assigned to `source_rank.tree`.
    expected
        The boolean value that `source_rank.readme_presence()` should return for the given `tree`.
    
    Returns
    -------
    None
        This function is a test and does not return a value; it raises an assertion error if the
        expectation is not met.
    """
    # Arrange
    source_rank.tree = tree
    # Act
    assert source_rank.readme_presence() == expected


@pytest.mark.parametrize("tree, expected", [("LICENSE", True), ("Licence.txt", True), ("README.md", False)])
def test_license_presence(source_rank, tree, expected):
    """
    Test license presence detection.
    
    This test verifies that the `license_presence` method of a `source_rank` object correctly identifies whether a given file name indicates the presence of a license. The test sets the `tree` attribute of the `source_rank` instance to the provided file name and asserts that the result of `license_presence()` matches the expected boolean value.
    
    Args:
        source_rank: The instance under test, expected to have a `tree` attribute and a `license_presence` method.
        tree: The file name or path to be assigned to `source_rank.tree` for the test.
        expected: The boolean value that `license_presence()` should return for the given `tree`.
    
    Returns:
        None
    """
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.license_presence() == expected


@pytest.mark.parametrize(
    "tree, expected",
    [("examples/", True), ("notebook.ipynb", True), ("source_code.py", False)],
)
def test_examples_presence(source_rank, tree, expected):
    """
    Test that the `examples_presence` method correctly identifies whether a given
    tree path contains examples.
    
    This test assigns the provided `tree` value to the `source_rank.tree` attribute
    and then asserts that the result of `source_rank.examples_presence()` matches
    the expected boolean value.
    
    Args:
        source_rank: The object under test, expected to have a `tree` attribute
            and an `examples_presence` method.
        tree: A string representing the path or filename to be set on
            `source_rank.tree`.
        expected: The boolean value that `source_rank.examples_presence()` is
            expected to return for the given `tree`.
    
    Returns:
        None
    """
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.examples_presence() == expected


@pytest.mark.parametrize(
    "tree, expected",
    [("docs/", True), ("documentation/index.html", True), ("source_code.py", False)],
)
def test_docs_presence(source_rank, tree, expected):
    """
    Test that the `docs_presence` method correctly identifies whether documentation
    files are present in the given source tree.
    
    Parameters
    ----------
    source_rank : object
        The instance under test. It is expected to have a `tree` attribute that
        can be set to a path string and a `docs_presence()` method that returns a
        boolean indicating the presence of documentation files.
    tree : str
        The path or identifier to assign to `source_rank.tree`. This value is
        used to simulate different source tree configurations.
    expected : bool
        The expected result of calling `source_rank.docs_presence()` after the
        `tree` attribute has been set.
    
    Returns
    -------
    None
        This function is a test and does not return a value.
    """
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.docs_presence() == expected


@pytest.mark.parametrize("tree, expected", [("tests/", True), ("unittest/", True), ("code/main.py", False)])
def test_tests_presence(source_rank, tree, expected):
    """
    Test that `SourceRank.tests_presence` correctly identifies whether a given
    directory path contains test files.
    
    Parameters
    ----------
    source_rank
        The `SourceRank` instance whose `tree` attribute will be set for the test.
    tree
        A string representing the directory path to assign to `source_rank.tree`.
    expected
        The expected boolean result from calling `source_rank.tests_presence()`.
    
    Returns
    -------
    None
    """
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.tests_presence() == expected


@pytest.mark.parametrize("tree, expected", [("requirements.txt", True), ("reqs.txt", False)])
def test_requirements_presence(source_rank, tree, expected):
    """
    Test that the source_rank correctly identifies the presence of a requirements file.
    
    Parameters
    ----------
    source_rank
        The SourceRank instance under test.
    tree
        The file name to assign to the source_rank's tree attribute.
    expected
        The expected boolean result indicating whether a requirements file is present.
    
    Returns
    -------
    None
        This test function performs an assertion and does not return a value.
    """
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.requirements_presence() == expected
