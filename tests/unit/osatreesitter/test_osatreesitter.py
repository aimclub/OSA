import pytest
import os
from unittest.mock import patch, mock_open, MagicMock, Mock
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter


@pytest.fixture
def osa_tree_sitter():
    """Создание фикстуры OSA_TreeSitter для повторного использования."""
    return OSA_TreeSitter("test_directory")


@patch("os.path.isdir", return_value=True)
@patch("os.walk", return_value=[("test_directory", [], ["script.py", "test.txt"])])
def test_files_list_directory(mock_walk, mock_isdir, osa_tree_sitter):
    """Test that files_list correctly identifies Python files in a directory."""
    # Act
    files, status = osa_tree_sitter.files_list("test_directory")
    expected_files = [os.path.join("test_directory", "script.py")]
    # Assert
    assert files == expected_files
    assert status == 0


@patch("os.path.isfile", return_value=True)
@patch("os.path.abspath", return_value="/absolute/path/to/script.py")
def test_files_list_file(mock_abspath, mock_isfile, osa_tree_sitter):
    """Test that files_list correctly handles a single file path."""
    # Act
    files, status = osa_tree_sitter.files_list("script.py")
    # Assert
    assert files == ["/absolute/path/to/script.py"]
    assert status == 1


def test_if_file_handler(osa_tree_sitter):
    """Test _if_file_handler returns the directory path."""
    # Arrange
    path = "/path/to/script.py"
    # Act
    result = osa_tree_sitter._if_file_handler(path)
    # Assert
    assert result == "/path/to"


@patch("builtins.open", new_callable=mock_open, read_data="print('Hello')")
def test_open_file(mock_file, osa_tree_sitter):
    """Test open_file correctly reads a file's content."""
    # Act
    content = osa_tree_sitter.open_file("script.py")
    # Assert
    assert content == "print('Hello')"


@patch("tree_sitter.Parser")
@patch("osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._parser_build")
@patch(
    "osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter.open_file",
    return_value="def test(): pass",
)
def test_parse_source_code(mock_open_file, mock_parser_build, mock_parser, osa_tree_sitter):
    """Test _parse_source_code returns a parsed tree."""
    # Arrange
    mock_parser_build.return_value = mock_parser
    mock_parser.parse.return_value = "mock_tree"
    # Act
    tree, source_code = osa_tree_sitter._parse_source_code("script.py")
    # Assert
    assert tree == "mock_tree"
    assert source_code == "def test(): pass"


@patch("osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._class_parser")
@patch("osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._function_parser")
@patch("osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._parse_source_code")
@patch(
    "osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._extract_imports",
    return_value={},
)
@patch(
    "osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._get_decorators",
    return_value=["mock_decorator"],
)
def test_extract_structure(
    mock_get_decorators,
    mock_extract_imports,
    mock_parse_source_code,
    mock_function_parser,
    mock_class_parser,
    osa_tree_sitter,
):
    """Test extract_structure processes functions, classes, and decorators in a Python file."""

    mock_tree = MagicMock()
    mock_tree.root_node = MagicMock()

    mock_decorated_node = MagicMock()
    mock_decorated_node.type = "decorated_definition"
    mock_function_node = MagicMock()
    mock_function_node.type = "function_definition"
    mock_decorated_node.children = [MagicMock(type="decorator"), mock_function_node]

    mock_class_node = MagicMock()
    mock_class_node.type = "class_definition"

    mock_tree.root_node.children = [
        mock_decorated_node,
        mock_class_node,
        mock_function_node,
    ]
    mock_parse_source_code.return_value = (mock_tree, "def test(): pass")

    def function_parser_side_effect(structure: dict, source_code, node, dec_list=[]):
        structure["structure"].append(f"mock_function_structure_{len(structure['structure'])}")
        return structure

    def class_parser_side_effect(structure: dict, source_code, node, dec_list=[]):
        structure["structure"].append(f"mock_class_structure_{len(structure['structure'])}")
        return structure

    mock_function_parser.side_effect = function_parser_side_effect
    mock_class_parser.side_effect = class_parser_side_effect

    result = osa_tree_sitter.extract_structure("script.py")

    assert result == {
        "structure": [
            "mock_function_structure_0",
            "mock_class_structure_1",
            "mock_function_structure_2",
        ],
        "imports": {},
    }

    mock_parse_source_code.assert_called_with("script.py")


@patch(
    "osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter.files_list",
    return_value=(["script.py"], 0),
)
@patch(
    "osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter.extract_structure",
    return_value=[{"type": "function", "name": "test"}],
)
def test_analyze_directory(mock_extract_structure, mock_files_list, osa_tree_sitter):
    """Test analyze_directory correctly processes all Python files."""
    # Act
    result = osa_tree_sitter.analyze_directory("test_directory")
    # Assert
    assert "script.py" in result
    assert result["script.py"] == [{"type": "function", "name": "test"}]


def test_resolve_import_path_from_import(osa_tree_sitter, tmp_path):
    """
    Test that the internal method `_resolve_import_path` correctly resolves an import
    statement to the corresponding module and file path.
    
    The test creates a temporary Python file named ``utils.py`` in a temporary
    directory, sets the current working directory of the ``osa_tree_sitter`` object
    to that directory, and then calls the private method
    ``_resolve_import_path`` with a simple import statement.  It verifies that
    the returned mapping contains the expected class name, module name, and file
    path.
    
    Args:
        osa_tree_sitter: The object under test that provides the
            ``_resolve_import_path`` method.
        tmp_path: A temporary directory path provided by the test framework
            (e.g., pytest) for creating test files.
    
    Returns:
        None
    """
    file = tmp_path / "utils.py"
    file.write_text("# dummy")
    osa_tree_sitter.cwd = str(tmp_path)

    with patch("os.path.exists", return_value=True):
        result = osa_tree_sitter._resolve_import_path("from utils import MyClass")

    assert "MyClass" in result
    assert result["MyClass"]["module"] == "utils"
    assert result["MyClass"]["path"].endswith("utils.py")


def test_resolve_import_path_with_alias(osa_tree_sitter, tmp_path):
    """
    Method Name: test_resolve_import_path_with_alias
    
    Test resolving an import statement that uses an alias. The test creates a temporary package structure, writes a dummy module file, sets the parser's current working directory, patches `os.path.exists` to always return `True`, and then calls the internal `_resolve_import_path` method. It verifies that the returned mapping contains the alias key, the correct module name, and a file path that ends with the expected module file.
    
    Args:
        osa_tree_sitter: The OsaTreeSitter instance being tested.
        tmp_path: A temporary directory path provided by the test framework.
    
    Returns:
        None
    """
    (tmp_path / "mypkg").mkdir()
    file = tmp_path / "mypkg" / "core.py"
    file.write_text("# dummy")
    osa_tree_sitter.cwd = str(tmp_path)

    with patch("os.path.exists", return_value=True):
        result = osa_tree_sitter._resolve_import_path("import mypkg.core as core")

    assert "core" in result
    assert result["core"]["module"] == "mypkg.core"
    assert result["core"]["path"].endswith("core.py")


def test_resolve_import_path_invalid_format(osa_tree_sitter):
    """
    Test that resolving an invalid import path returns an empty dictionary.
    
    Args:
        osa_tree_sitter: The tree-sitter parser instance used for resolving import paths.
    
    Returns:
        None
    """
    assert osa_tree_sitter._resolve_import_path("not an import") == {}


def test_extract_imports_parses_nodes(osa_tree_sitter):
    """
    Test that the `_extract_imports` method correctly parses different types of import
    nodes and returns a dictionary containing the expected import entries.
    
    The test constructs mock AST nodes representing an `import_statement` and an
    `import_from_statement`, patches the internal `_resolve_import_path` method to
    return predetermined import information, and then verifies that the result
    includes the expected keys for the imported modules or symbols.
    
    Args:
        osa_tree_sitter: The instance of the class under test, providing the
            `_extract_imports` method and the `_resolve_import_path` helper.
    
    Returns:
        None
    """
    node1 = Mock()
    node1.type = "import_statement"
    node1.text = b"import os"

    node2 = Mock()
    node2.type = "import_from_statement"
    node2.text = b"from math import sqrt"

    root_node = Mock()
    root_node.children = [node1, node2]

    with patch.object(osa_tree_sitter, "_resolve_import_path") as mock_resolve:
        mock_resolve.side_effect = [
            {"os": {"module": "os", "path": "/fake/os.py"}},
            {"sqrt": {"module": "math", "class": "sqrt", "path": "/fake/math.py"}},
        ]
        result = osa_tree_sitter._extract_imports(root_node)

    assert "os" in result and "sqrt" in result


def test_resolve_import_with_function(osa_tree_sitter):
    """
    Test that the internal _resolve_import method correctly resolves a function
    import from a given alias.
    
    This test constructs a simple imports mapping where the alias ``np`` refers to
    the ``numpy`` module. It then calls the private ``_resolve_import`` method on
    the provided ``osa_tree_sitter`` instance to resolve the fully qualified
    function name ``np.array``. The test verifies that the returned dictionary
    contains the expected module name and function name.
    
    Parameters
    ----------
    osa_tree_sitter
        The instance of the tree-sitter wrapper that provides the
        ``_resolve_import`` method.
    
    Returns
    -------
    None
        This function performs assertions and does not return a value.
    """
    imports = {"np": {"module": "numpy", "path": "/numpy.py"}}
    result = osa_tree_sitter._resolve_import("np.array", "np", imports)
    assert result["module"] == "numpy"
    assert result["function"] == "array"


def test_resolve_import_class_method_chain(osa_tree_sitter):
    """
    Test that the `_resolve_import` method correctly resolves a class method chain.
    
    Args:
        osa_tree_sitter: The OsaTreeSitter instance used to resolve imports.
    
    Returns:
        None
    
    Raises:
        AssertionError: If the resolved class or function does not match the expected values.
    """
    imports = {"mod": {"module": "pkg.module", "class": "MyClass", "path": "/module.py"}}
    result = osa_tree_sitter._resolve_import("mod.MyClass().run", "mod", imports)
    assert result["class"] == "MyClass"
    assert result["function"] == "MyClass().run"


def test_resolve_import_unknown(osa_tree_sitter):
    """
    Test that resolving an unknown import returns an empty dictionary.
    
    This test verifies that the `_resolve_import` method of the
    `osa_tree_sitter` object correctly handles a case where the
    requested import cannot be found.  It calls the method with a
    non‑existent module name and asserts that the result is an empty
    dictionary, indicating that no symbols were imported.
    
    Args:
        osa_tree_sitter: The instance providing the `_resolve_import`
            method, typically a parser or resolver object used in the
            test suite.
    
    Returns:
        None
    """
    assert osa_tree_sitter._resolve_import("foo.bar", "foo", {}) == {}
