import os
import shutil

from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter  # adjust import path
from tests.utils.fixtures.osatreesitter import Node


def test_files_list_directory(tmp_path, temp_dir_with_files):
    # Arrange
    repo_path, expected_files = temp_dir_with_files

    # Act
    files, status = OSA_TreeSitter(tmp_path).files_list(repo_path)

    # Assert
    assert status == 0
    assert all(f in files for f in expected_files)
    assert not any(f.endswith(".txt") for f in files)


def test_files_list_single_file(tmp_path, temp_py_file):
    # Aсt
    files, status = OSA_TreeSitter(tmp_path).files_list(temp_py_file)

    # Assert
    assert status == 1
    assert files == [os.path.abspath(temp_py_file)]


def test_files_list_non_py_file(tmp_path):
    # Arrange
    file = tmp_path / "note.txt"
    file.write_text("hello")

    # Act
    files, status = OSA_TreeSitter(tmp_path).files_list(str(file))

    # Assert
    assert files == []
    assert status == 0


def test_files_ignore_list(temp_dir_with_ignores):
    repo_path, res = temp_dir_with_ignores
    ignore_list = ["ignore1", "allow1/ignore2", "__init__.py"]

    files, _ = OSA_TreeSitter(repo_path, ignore_list).files_list(repo_path)

    assert files == res


def test_if_file_handler_returns_dir(temp_py_file):
    # Arrange
    parent_dir = os.path.dirname(temp_py_file)

    # Assert
    assert OSA_TreeSitter._if_file_handler(temp_py_file) == parent_dir


def test_open_file_reads_content(temp_py_file):
    # Act
    content = OSA_TreeSitter.open_file(temp_py_file)

    # Assert
    assert "x = 1" in content
    assert "y = 2" in content


def test_parser_build_and_parse(temp_py_file):
    # Arrange
    ts = OSA_TreeSitter(os.path.dirname(temp_py_file))

    # Act
    parser = ts._parser_build(temp_py_file)

    # Assert
    assert parser is not None

    tree, source = ts._parse_source_code(temp_py_file)
    assert "x = 1" in source
    assert hasattr(tree, "root_node")


def test_traverse_expression_adds_identifiers():
    # Arrange
    ts = OSA_TreeSitter(".")

    # Fake tree-sitter node using a minimal stub
    class Node:
        def __init__(self, type_, children=None, text=None):
            self.type = type_
            self.children = children or []
            self.text = text

    identifier = Node("identifier", text=b"foo")
    assignment = Node("assignment", children=[identifier])
    expr_node = Node("expr", children=[assignment])

    # Act
    attrs = ts._traverse_expression([], expr_node)

    # Assert
    assert "foo" in attrs


def test_get_attributes_calls_traverse_expression(monkeypatch):
    # Arrange
    ts = OSA_TreeSitter(".")
    called = {}

    def fake_traverse(attrs, node):
        called["ok"] = True
        return attrs + ["bar"]

    monkeypatch.setattr(ts, "_traverse_expression", fake_traverse)

    class Node:
        def __init__(self, type_, children=None):
            self.type = type_
            self.children = children or []

    expr_stmt = Node("expression_statement")
    block_node = Node("block", children=[expr_stmt])

    # Act
    attrs = ts._get_attributes([], block_node)

    # Assert
    assert "bar" in attrs
    assert called["ok"] is True


def test_class_parser_appends_structure(monkeypatch):
    # Arrange
    ts = OSA_TreeSitter(".")

    # monkeypatch dependencies
    monkeypatch.setattr(ts, "_get_attributes", lambda attrs, node: ["attr1"])
    monkeypatch.setattr(ts, "_get_docstring", lambda node: "docstring here")
    monkeypatch.setattr(ts, "_traverse_block", lambda block, src, imports: [{"method": "from_block"}])
    monkeypatch.setattr(ts, "_extract_function_details", lambda node, src, imports: {"method": "from_func"})

    block_node = Node("block")
    func_node = Node("function_definition")
    class_node = Node("class_definition", children=[block_node, func_node], name="MyClass")

    structure = {"structure": [], "imports": {}}

    # Act
    ts._class_parser(structure, "source_code_here", class_node, dec_list=["@decor"])

    # Assert
    result = structure["structure"][0]
    assert result["type"] == "class"
    assert result["name"] == "MyClass"
    assert result["decorators"] == ["@decor"]
    assert "attr1" in result["attributes"]
    assert result["docstring"] == "docstring here"
    assert any("method" in m for m in result["methods"])


def test_function_parser_appends_structure(monkeypatch):
    # Arrange
    ts = OSA_TreeSitter(".")
    monkeypatch.setattr(ts, "_extract_function_details", lambda node, src, imports, dec_list=None: {"name": "myfunc"})

    node = Node("function_definition", start_point=(4, 0))
    structure = {"structure": [], "imports": {}}

    # Act
    ts._function_parser(structure, "src", node, dec_list=["@dec"])

    # Assert
    result = structure["structure"][0]
    assert result["type"] == "function"
    assert result["start_line"] == 5  # 0-based to 1-based
    assert result["details"]["name"] == "myfunc"


def test_get_decorators_with_identifier_and_call():
    # Arrange
    ts = OSA_TreeSitter(".")
    identifier = Node("identifier", text=b"deco1")
    call = Node("call", text=b"deco2()")
    dec_node = Node("decorators", children=[identifier, call])

    # Act
    result = ts._get_decorators([], dec_node)

    # Assert
    assert "@deco1" in result
    assert "@deco2()" in result


def test_resolve_import_from_with_alias(tmp_path):
    # Arrange
    ts = OSA_TreeSitter(str(tmp_path))

    module_file = tmp_path / "mymod.py"
    module_file.write_text("class Foo: pass")

    text = "from mymod import Foo as Bar"

    # Act
    result = ts._resolve_import_path(text)

    # Assert
    assert "Bar" in result
    assert result["Bar"]["class"] == "Foo"
    assert result["Bar"]["module"] == "mymod"
    assert result["Bar"]["path"].endswith("mymod.py")


def test_resolve_import_simple(tmp_path):
    # Arrange
    ts = OSA_TreeSitter(str(tmp_path))
    module_file = tmp_path / "simplemod.py"
    module_file.write_text("")

    text = "import simplemod"

    # Act
    result = ts._resolve_import_path(text)

    # Assert
    assert "simplemod" in result
    assert result["simplemod"]["module"] == "simplemod"


def test_resolve_import_with_as(tmp_path):
    # Arrange
    ts = OSA_TreeSitter(str(tmp_path))
    module_file = tmp_path / "aliasmod.py"
    module_file.write_text("")

    text = "import aliasmod as am"

    # Act
    result = ts._resolve_import_path(text)

    # Assert
    assert "am" in result
    assert result["am"]["module"] == "aliasmod"


def test_resolve_import_invalid_string_returns_empty():
    # Arrange
    ts = OSA_TreeSitter(".")

    # Act
    result = ts._resolve_import_path("not an import")

    # Asset
    assert result == {}


def test_extract_imports(monkeypatch):
    # Arrange
    ts = OSA_TreeSitter(".")
    called = {}

    def fake_resolve(text):
        called["ok"] = True
        return {"x": {"module": "m", "path": "p"}}

    monkeypatch.setattr(ts, "_resolve_import_path", fake_resolve)
    import_node = Node("import_statement", text=b"import x")
    root_node = Node("root", children=[import_node])

    # Act
    result = ts._extract_imports(root_node)

    # Assert
    assert "x" in result
    assert called["ok"]


def test_resolve_import_simple_alias(tmp_path):
    # Arrange
    ts = OSA_TreeSitter(str(tmp_path))
    imports = {"mymod": {"module": "mymod", "path": "p.py"}}

    # Act
    result = ts._resolve_import("mymod", "mymod", imports, {})

    # Assert
    assert result["module"] == "mymod"
    assert result["path"] == "p.py"
    assert result["function"] is None


def test_resolve_import_function_call():
    # Arrange
    ts = OSA_TreeSitter(".")
    imports = {"m": {"module": "m", "path": "p"}}

    # Act
    result = ts._resolve_import("m.do_something", "m", imports, {})

    # Assert
    assert result["function"] == "do_something"


def test_resolve_import_class_and_method():
    # Arrange
    ts = OSA_TreeSitter(".")
    imports = {"m": {"module": "m", "path": "p"}}

    # Act
    result = ts._resolve_import("m.MyClass().run", "m", imports, {})

    # Assert
    assert result["class"] == "MyClass"
    assert result["function"] == "MyClass().run"


def test_resolve_import_unknown_alias_returns_empty():
    # Arrange
    ts = OSA_TreeSitter(".")

    # Act
    result = ts._resolve_import("x.y", "x", {}, {})

    # Assert
    assert result == {}


def test_resolve_method_calls_with_assignment():
    # Arrange
    ts = OSA_TreeSitter(".")
    imports = {"m": {"module": "m", "path": "p"}}

    func_node = Node("identifier", text=b"m.do", start_byte=0, end_byte=4)
    call_node = Node("call", field_function=func_node)
    call_node.field_function = func_node

    identifier = Node("identifier", text=b"alias")
    assign_node = Node("assignment", children=[identifier, call_node])
    expr = Node("expr", children=[assign_node])
    block = Node("block", children=[expr])
    function_node = Node("function_definition", children=[block])

    # Act
    result = ts._resolve_method_calls(function_node, "m.do()", imports)

    # Assert - returns list of function name strings
    assert isinstance(result, list)
    assert "m.do" in result


def test_resolve_method_calls_direct_call():
    # Arrange
    ts = OSA_TreeSitter(".")
    imports = {"m": {"module": "m", "path": "p"}}

    func_node = Node("identifier", text=b"m.work", start_byte=0, end_byte=6)
    call_node = Node("call", children=[], field_function=func_node)
    call_node.field_function = func_node

    expr = Node("expr", children=[call_node])
    block = Node("block", children=[expr])
    function_node = Node("function_definition", children=[block])

    # Act
    result = ts._resolve_method_calls(function_node, "m.work()", imports)

    # Assert - returns list of function name strings
    assert isinstance(result, list)
    assert "m.work" in result


def test_resolve_method_calls_no_block_returns_empty():
    # Arrange
    ts = OSA_TreeSitter(".")
    fn_node = Node("function_definition", children=[])

    # Act
    result = ts._resolve_method_calls(fn_node, "src", {})

    # Assert
    assert result == []


def test_extract_structure_orchestrates(monkeypatch):
    # Arrange
    ts = OSA_TreeSitter(".")

    # Patch parse and extract
    fake_tree = type(
        "T",
        (),
        {"root_node": Node("root", children=[Node("function_definition"), Node("class_definition")])},
    )
    monkeypatch.setattr(ts, "_parse_source_code", lambda filename: (fake_tree, "src"))
    monkeypatch.setattr(ts, "_extract_imports", lambda root: {"imp": {"module": "m", "path": "p"}})

    called = {"func": False, "cls": False}
    monkeypatch.setattr(ts, "_function_parser", lambda s, sc, n, dec_list=None: called.__setitem__("func", True))
    monkeypatch.setattr(ts, "_class_parser", lambda s, sc, n, dec_list=None: called.__setitem__("cls", True))

    # Act
    result = ts.extract_structure("file.py")

    # Assert
    assert "structure" in result
    assert "imports" in result
    assert called["func"] and called["cls"]


def test_get_docstring_from_block():
    # Arrange
    ts = OSA_TreeSitter(".")

    string_node = Node("string", text=b'"Docstring here"')
    expr = Node("expression_statement", children=[string_node])
    block = Node("block", children=[expr])

    # Act
    result = ts._get_docstring(block)

    # Assert
    assert "Docstring here" in result


def test_traverse_block(monkeypatch):
    # Arrange
    ts = OSA_TreeSitter(".")

    fake_method = {"method_name": "foo"}
    monkeypatch.setattr(ts, "_extract_function_details", lambda *a, **k: fake_method)
    monkeypatch.setattr(ts, "_get_decorators", lambda l, d: ["@dec"])

    func_def = Node("function_definition")
    decorator = Node("decorator")
    decorated = Node("decorated_definition", children=[decorator, func_def])
    block = Node("block", children=[decorated, func_def])

    # Act
    result = ts._traverse_block(block, "code", {})

    # Assert
    assert fake_method in result
    assert len(result) == 2


def test_extract_function_details(monkeypatch):
    # Arrange
    ts = OSA_TreeSitter(".")
    monkeypatch.setattr(ts, "_get_docstring", lambda node: "doc")
    monkeypatch.setattr(ts, "_resolve_method_calls", lambda *a: [{"function": "call"}])

    name_node = Node("identifier", text=b"my_func")
    param_id = Node("identifier", text=b"x")
    params_node = Node("parameters", children=[param_id])
    block = Node("block", children=[Node("string", text=b"'doc'")])
    func_node = Node(
        "function_definition",
        children=[name_node, params_node, block],
        start_point=(0, 0),
        start_byte=0,
        end_byte=10,
        name="my_func",
    )

    # Act
    result = ts._extract_function_details(func_node, "def my_func(x): pass", {}, ["@dec"])

    # Assert
    assert result["method_name"] == "my_func"
    assert "x" in result["arguments"]
    assert result["docstring"] == "doc"
    assert result["method_calls"][0]["function"] == "call"


def test_analyze_directory(monkeypatch, tmp_path):
    # Arrange
    ts = OSA_TreeSitter(".")
    fake_file = tmp_path / "test.py"
    fake_file.write_text("print('hi')")

    monkeypatch.setattr(ts, "files_list", lambda p: ([str(fake_file)], True))
    monkeypatch.setattr(ts, "extract_structure", lambda f: {"imports": {}, "structure": []})

    # Act
    results = ts.analyze_directory(str(tmp_path))

    # Assert
    assert str(fake_file) in results


def test_show_results(monkeypatch, caplog):
    # Arrange
    ts = OSA_TreeSitter(".")
    caplog.set_level("INFO")
    results = {
        "file.py": {
            "structure": [
                {
                    "type": "class",
                    "name": "C",
                    "start_line": 1,
                    "docstring": "doc",
                    "methods": [
                        {
                            "method_name": "m",
                            "arguments": ["x"],
                            "return_type": "int",
                            "start_line": 2,
                            "docstring": None,
                            "source_code": "def m(x): pass",
                        }
                    ],
                },
                {
                    "type": "function",
                    "details": {
                        "method_name": "f",
                        "arguments": [],
                        "return_type": None,
                        "start_line": 1,
                        "docstring": None,
                        "source_code": "def f(): pass",
                    },
                },
            ],
            "imports": {},
        }
    }

    # Act
    ts.show_results(results)

    # Assert
    assert "Class: C" in caplog.text
    assert "Function: f" in caplog.text


def test_log_results(tmp_path, monkeypatch):
    # Arrange
    ts = OSA_TreeSitter(".")
    ts.cwd = str(tmp_path)
    monkeypatch.chdir(tmp_path)

    results = {
        "file.py": {
            "structure": [
                {
                    "type": "class",
                    "name": "C",
                    "start_line": 1,
                    "docstring": None,
                    "methods": [
                        {
                            "method_name": "m",
                            "arguments": [],
                            "return_type": None,
                            "start_line": 2,
                            "docstring": None,
                            "source_code": "def m(): pass",
                        }
                    ],
                }
            ],
            "imports": {},
        }
    }

    # Act
    ts.log_results(results)

    # Assert
    report = tmp_path / "examples" / "report.txt"
    assert report.exists()
    text = report.read_text(encoding="utf-8")
    assert "Class: C" in text
    assert "Method: m" in text

    # Cleanup
    shutil.rmtree(tmp_path / "examples")
