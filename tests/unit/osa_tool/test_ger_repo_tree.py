from osa_tool.utils import get_repo_tree


def test_get_repo_tree_excludes_git_and_binaries(tmp_path):
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
