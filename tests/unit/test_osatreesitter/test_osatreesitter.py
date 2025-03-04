import pytest
import os
from unittest.mock import patch, mock_open, MagicMock
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter


@pytest.fixture
def osa_tree_sitter():
    """Создание фикстуры OSA_TreeSitter для повторного использования."""
    return OSA_TreeSitter("test_directory")


@patch("os.path.isdir", return_value=True)
@patch("os.walk", return_value=[("test_directory", [], ["script.py", "test.txt"])])
def test_files_list_directory(mock_walk, mock_isdir, osa_tree_sitter):
    """Test that files_list correctly identifies Python files in a directory."""
    files, status = osa_tree_sitter.files_list("test_directory")

    expected_files = [os.path.join("test_directory", "script.py")]

    assert files == expected_files
    assert status == 0


@patch("os.path.isfile", return_value=True)
@patch("os.path.abspath", return_value="/absolute/path/to/script.py")
def test_files_list_file(mock_abspath, mock_isfile, osa_tree_sitter):
    """Test that files_list correctly handles a single file path."""
    files, status = osa_tree_sitter.files_list("script.py")
    assert files == ["/absolute/path/to/script.py"]
    assert status == 1


def test_if_file_handler(osa_tree_sitter):
    """Test _if_file_handler returns the directory path."""
    path = "/path/to/script.py"
    result = osa_tree_sitter._if_file_handler(path)
    assert result == "/path/to"


@patch("builtins.open", new_callable=mock_open, read_data="print('Hello')")
def test_open_file(mock_file, osa_tree_sitter):
    """Test open_file correctly reads a file's content."""
    content = osa_tree_sitter.open_file("script.py")
    assert content == "print('Hello')"


@patch("tree_sitter.Parser")
@patch("osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._parser_build")
@patch(
    "osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter.open_file",
    return_value="def test(): pass",
)
def test_parse_source_code(
    mock_open_file, mock_parser_build, mock_parser, osa_tree_sitter
):
    """Test _parse_source_code returns a parsed tree."""
    mock_parser_build.return_value = mock_parser
    mock_parser.parse.return_value = "mock_tree"

    tree, source_code = osa_tree_sitter._parse_source_code("script.py")

    assert tree == "mock_tree"
    assert source_code == "def test(): pass"


@patch("osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._class_parser")
@patch("osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._function_parser")
@patch("osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._parse_source_code")
@patch(
    "osa_tool.osatreesitter.osa_treesitter.OSA_TreeSitter._get_decorators",
    return_value=["mock_decorator"],
)
def test_extract_structure(
    mock_get_decorators,
    mock_parse_source_code,
    mock_function_parser,
    mock_class_parser,
    osa_tree_sitter,
):
    """Test extract_structure processes functions, classes, and decorators in a Python file."""

    with patch.object(
        OSA_TreeSitter, "_function_parser"
    ) as mock_function_parser, patch.object(
        OSA_TreeSitter, "_class_parser"
    ) as mock_class_parser:

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

        def function_parser_side_effect(structure, source_code, node, dec_list=[]):
            new_structure = structure.copy()
            new_structure.append(f"mock_function_structure_{len(new_structure)}")
            return new_structure

        def class_parser_side_effect(structure, source_code, node, dec_list=[]):
            new_structure = structure.copy()
            new_structure.append(f"mock_class_structure_{len(new_structure)}")
            return new_structure

        mock_function_parser.side_effect = function_parser_side_effect
        mock_class_parser.side_effect = class_parser_side_effect

        result = osa_tree_sitter.extract_structure("script.py")

        print(mock_get_decorators.call_args_list)
        print(mock_function_parser.call_args_list)

        mock_get_decorators.assert_called_with([], mock_decorated_node.children[0])
        mock_function_parser.assert_any_call(
            [], "def test(): pass", mock_decorated_node.children[1], ["mock_decorator"]
        )
        mock_class_parser.assert_any_call(
            ["mock_function_structure_0"], "def test(): pass", mock_class_node
        )
        mock_function_parser.assert_any_call(
            ["mock_function_structure_0", "mock_class_structure_1"],
            "def test(): pass",
            mock_function_node,
        )

        assert result == [
            "mock_function_structure_0",
            "mock_class_structure_1",
            "mock_function_structure_2",
        ]

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
    result = osa_tree_sitter.analyze_directory("test_directory")
    assert "script.py" in result
    assert result["script.py"] == [{"type": "function", "name": "test"}]
