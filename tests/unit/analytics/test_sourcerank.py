import pytest


@pytest.mark.parametrize(
    "tree, expected",
    [("README.md", True), ("readme.txt", True), ("docs/guide.pdf", False)],
)
def test_readme_presence(source_rank, tree, expected):
    # Arrange
    source_rank.tree = tree
    # Act
    assert source_rank.readme_presence() == expected


@pytest.mark.parametrize("tree, expected", [("LICENSE", True), ("Licence.txt", True), ("README.md", False)])
def test_license_presence(source_rank, tree, expected):
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.license_presence() == expected


@pytest.mark.parametrize(
    "tree, expected",
    [("examples/", True), ("notebook.ipynb", True), ("source_code.py", False)],
)
def test_examples_presence(source_rank, tree, expected):
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.examples_presence() == expected


@pytest.mark.parametrize(
    "tree, expected",
    [("docs/", True), ("documentation/index.html", True), ("source_code.py", False)],
)
def test_docs_presence(source_rank, tree, expected):
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.docs_presence() == expected


@pytest.mark.parametrize("tree, expected", [("tests/", True), ("unittest/", True), ("code/main.py", False)])
def test_tests_presence(source_rank, tree, expected):
    # Arrange
    source_rank.tree = tree
    # Assert
    assert source_rank.tests_presence() == expected
