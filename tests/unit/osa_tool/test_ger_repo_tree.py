from osa_tool.utils import get_repo_tree


def test_get_repo_tree_excludes_git_and_binaries(tmp_path):
    """
    Test that `get_repo_tree` correctly excludes the `.git` directory and non-Python
    files from the repository tree.
    
    The test creates a temporary directory structure containing a `.git` folder,
    a Python file, a CSV file, and a subdirectory with another Python file. It
    then calls `get_repo_tree` on the temporary path and verifies that the
    returned tree string includes the Python files but does not include the
    `.git` directory or the CSV file.
    
    Args:
        tmp_path: A temporary directory path provided by pytest for test isolation.
    
    Returns:
        None
    """
    # Arrange
    (tmp_path / ".git").mkdir()
    (tmp_path / "main.py").write_text("print('hello')")
    (tmp_path / "data.csv").write_text("a,b,c")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "utils.py").write_text("# utils")
    # Act
    tree = get_repo_tree(str(tmp_path))
    lines = tree.splitlines()
    # Assert
    assert "main.py" in lines
    assert "subdir/utils.py" in lines
    assert ".git" not in tree
    assert "data.csv" not in tree
