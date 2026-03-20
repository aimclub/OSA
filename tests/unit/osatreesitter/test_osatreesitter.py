import os
import shutil

from osa_tool.operations.codebase.docstring_generation.osa_treesitter import OSA_TreeSitter  # adjust import path
from tests.utils.fixtures.osatreesitter import Node


def test_files_list_directory(tmp_path, temp_dir_with_files):
    """
    Tests the functionality of listing files within a directory using the OSA_TreeSitter class.
    
    This test verifies that the files_list method correctly identifies and returns a list of relevant files from a given repository path, ensures the operation status is successful, and confirms that unwanted file types (like .txt) are excluded from the results.
    
    Args:
        tmp_path: A temporary directory path provided by the test framework, used to instantiate the OSA_TreeSitter object.
        temp_dir_with_files: A fixture providing a tuple containing the repository path to test and the list of expected files that should be included.
    
    Steps:
        1. Arrange: Unpack the fixture to obtain the repository path and the expected list of files.
        2. Act: Call the files_list method on an OSA_TreeSitter instance, passing the repository path.
        3. Assert: 
           - Check that the returned status indicates a directory was processed (status == 0).
           - Verify that all expected files are present in the returned list.
           - Ensure no files with a .txt extension appear in the results.
    
    Why:
        The test ensures the files_list method properly filters file types and returns the correct status when given a directory path, which is a core requirement for the tool's repository analysis pipeline.
    """
    # Arrange
    repo_path, expected_files = temp_dir_with_files

    # Act
    files, status = OSA_TreeSitter(tmp_path).files_list(repo_path)

    # Assert
    assert status == 0
    assert all(f in files for f in expected_files)
    assert not any(f.endswith(".txt") for f in files)


def test_files_list_single_file(tmp_path, temp_py_file):
    """
    Tests the ability of the OSA_TreeSitter class to list a single file.
    
    Args:
        tmp_path: The temporary directory path used for the test environment.
        temp_py_file: The path to a temporary Python file to be listed.
    
    Returns:
        None.
    
    Why:
        This test verifies that the OSA_TreeSitter.files_list method correctly handles a single file input, returning a list containing only that file's absolute path and a success status. It ensures the method's behavior is as expected for individual file queries, which is a foundational case for file listing operations.
    """
    # Aсt
    files, status = OSA_TreeSitter(tmp_path).files_list(temp_py_file)

    # Assert
    assert status == 1
    assert files == [os.path.abspath(temp_py_file)]


def test_files_list_non_py_file(tmp_path):
    """
    Verifies that the files_list method correctly ignores non-Python files.
    
    This test case creates a text file (note.txt) in a temporary directory, processes it using an OSA_TreeSitter instance, and asserts that the resulting file list is empty and the status code is zero. This ensures that only Python files are included in the output, which is necessary because the OSA Tool is designed to analyze and document Python repositories specifically.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path for file creation.
    """
    # Arrange
    file = tmp_path / "note.txt"
    file.write_text("hello")

    # Act
    files, status = OSA_TreeSitter(tmp_path).files_list(str(file))

    # Assert
    assert files == []
    assert status == 0


def test_files_ignore_list(temp_dir_with_ignores):
    """
    Verifies that the file discovery process correctly excludes files specified in an ignore list.
    
    Args:
        temp_dir_with_ignores: A tuple containing the path to a temporary repository directory and the expected list of filtered file paths. The test uses this fixture to set up a test repository and the expected result.
    
    Why:
        This test ensures that the OSA_TreeSitter file discovery respects the provided ignore patterns, which is critical for focusing analysis only on relevant source files and avoiding unnecessary or private files.
    
    Returns:
        None.
    """
    repo_path, res = temp_dir_with_ignores
    ignore_list = ["ignore1", "allow1/ignore2", "__init__.py"]

    files, _ = OSA_TreeSitter(repo_path, ignore_list).files_list(repo_path)

    assert files == res


def test_if_file_handler_returns_dir(temp_py_file):
    """
    Verifies that the _if_file_handler method correctly returns the parent directory of a given file path.
    
    Args:
        temp_py_file: The path to a temporary Python file used for testing. This fixture provides a file path for the test.
    
    Why:
        This test ensures that the _if_file_handler method, which is part of the OSA_TreeSitter class, accurately computes and returns the parent directory of a file path. This functionality is important for the OSA Tool's repository analysis and documentation generation, as it often needs to determine directory contexts when processing files.
    """
    # Arrange
    parent_dir = os.path.dirname(temp_py_file)

    # Assert
    assert OSA_TreeSitter._if_file_handler(temp_py_file) == parent_dir


def test_open_file_reads_content(temp_py_file):
    """
    Verifies that the open_file method correctly reads and returns the content of a given file.
    This test ensures the file reading functionality works as expected, which is foundational for many other operations in the OSA Tool that rely on accessing file contents.
    
    Args:
        temp_py_file: The path to a temporary Python file used for testing. The file contains predefined content ("x = 1" and "y = 2") to validate the reading operation.
    """
    # Act
    content = OSA_TreeSitter.open_file(temp_py_file)

    # Assert
    assert "x = 1" in content
    assert "y = 2" in content


def test_parser_build_and_parse(temp_py_file):
    """
    Tests the building of a parser and the parsing of source code from a temporary file.
    
    This test method initializes an OSA_TreeSitter instance, builds a parser for a specific Python file, and verifies that the source code is correctly read and parsed into a tree structure with a root node. It ensures the parser is successfully constructed and that the source code reading and tree generation work as expected.
    
    Args:
        temp_py_file: The path to the temporary Python file used for testing. The file contains a simple Python statement ("x = 1") which is verified to be present in the parsed source.
    
    Why:
    - The test validates that the parser building logic (`_parser_build`) correctly creates a parser object for the given file.
    - It also checks that the source code parsing (`_parse_source_code`) correctly reads the file content and produces a valid syntax tree with a root node, confirming the integration of these components works in the OSA_TreeSitter class.
    """
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
    """
    Tests that the `_traverse_expression` method correctly identifies and adds identifier names to the attributes list.
    
    This test case simulates a tree-sitter node structure containing an identifier "foo" nested within an assignment and expression. It verifies that the traversal logic successfully extracts the text from the identifier node and includes it in the resulting collection.
    
    The test uses a manually constructed mock node hierarchy to isolate and validate the traversal behavior without external dependencies.
    
    Args:
        None
    
    Returns:
        None
    """
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
    """
    Verifies that the _get_attributes method correctly calls the internal _traverse_expression method.
    
    This test uses a monkeypatch to replace the _traverse_expression method with a mock function, ensuring that when a block node containing an expression statement is processed, the traversal logic is triggered and the returned attributes are updated accordingly.
    
    Args:
        monkeypatch: A pytest fixture used to mock the _traverse_expression method of the OSA_TreeSitter instance.
    
    Why:
        This test ensures the internal traversal method is invoked as expected during attribute extraction, confirming the method's integration and correct flow when handling expression statements within block nodes.
    """
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
    """
    Verifies that the `_class_parser` method correctly parses a class definition and appends the resulting metadata structure to the provided list.
    
    This test ensures the parser extracts class details—such as name, decorators, attributes, docstring, and methods—and appends a complete class metadata dictionary to the structure list. It uses mocking to isolate the parser from its dependencies, allowing focused validation of the parsing logic.
    
    Args:
        monkeypatch: A pytest fixture used to mock dependencies and internal methods of the OSA_TreeSitter instance, including `_get_attributes`, `_get_docstring`, `_traverse_block`, and `_extract_function_details`.
    
    Returns:
        None.
    """
    # Arrange
    ts = OSA_TreeSitter(".")

    # monkeypatch dependencies
    monkeypatch.setattr(ts, "_get_attributes", lambda attrs, node: ["attr1"])
    monkeypatch.setattr(ts, "_get_docstring", lambda node: "docstring here")
    monkeypatch.setattr(ts, "_traverse_block", lambda class_name, block, src, imports: [{"method": "from_block"}])
    monkeypatch.setattr(ts, "_extract_function_details", lambda node, src, imports, class_name: {"method": "from_func"})

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
    """
    Verifies that the `_function_parser` method correctly extracts function details and appends the resulting metadata structure to the provided list.
    
    Args:
        monkeypatch: A pytest fixture used to mock the `_extract_function_details` method to return a controlled dictionary.
    
    Why:
        This test ensures that the internal `_function_parser` method properly processes a function node, converts its start line from 0‑based to 1‑based indexing, and appends a complete function metadata entry to the structure list. Mocking `_extract_function_details` isolates the test to focus on the parser’s integration and data‑handling logic.
    
    Note:
        This is a test method and does not initialize class fields or return any values.
    """
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
    """
    Verifies that the `_get_decorators` method correctly extracts and formats decorator names from a syntax tree node containing both simple identifiers and function calls.
    
    This test case simulates a Tree-sitter node structure where one decorator is a plain identifier and another is a call expression, ensuring both are returned with the appropriate '@' prefix. The test is necessary because decorators can appear in different syntactic forms, and the method must handle each correctly to produce a complete list of decorators for documentation purposes.
    
    Args:
        None.
    
    Returns:
        None.
    """
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
    """
    Tests the resolution of an 'import from' statement that includes an alias.
    
    This test verifies that the OSA_TreeSitter instance correctly resolves an import statement
    where a class is imported with an alias, ensuring the alias is properly mapped to the original
    class and its source module. This is important for accurately tracking dependencies and
    symbol definitions in code analysis.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path for file operations.
    
    Returns:
        None: This method performs assertions and does not return a value.
    """
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
    """
    Tests the basic resolution of a module import path using the OSA_TreeSitter class.
        
        This test verifies that a simple, direct import statement (e.g., "import simplemod") is correctly resolved to its corresponding module path. It creates a mock module file in a temporary directory to simulate a real Python module, ensuring the resolver can locate it.
        
        Args:
            tmp_path: A temporary directory path provided by the test framework used for creating mock module files.
        
        Returns:
            None.
    """
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
    """
    Verifies that the _resolve_import_path method correctly handles Python import statements using the 'as' alias syntax.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path used to create a dummy module file.
    
    Why:
        This test ensures that when an import statement includes an alias (e.g., 'import module as alias'), the method properly maps the alias to the original module name, which is critical for accurate import resolution in code analysis.
    
    Returns:
        None.
    """
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
    """
    Verifies that the _resolve_import_path method returns an empty dictionary when provided with an invalid import string.
    
    This test case initializes an OSA_TreeSitter instance and checks that passing a non-import string to the internal path resolution logic results in an empty result set, ensuring robust handling of malformed input. This is important because the tool must gracefully handle incorrect or unexpected input without crashing, maintaining overall system reliability.
    
    Args:
        ts: An instance of OSA_TreeSitter initialized with the current directory.
        result: The output from calling _resolve_import_path with the string "not an import".
    
    The test follows the Arrange-Act-Assert pattern:
    - Arrange: Create an OSA_TreeSitter instance.
    - Act: Call _resolve_import_path with a clearly invalid import string.
    - Assert: Verify the result is an empty dictionary.
    """
    # Arrange
    ts = OSA_TreeSitter(".")

    # Act
    result = ts._resolve_import_path("not an import")

    # Asset
    assert result == {}


def test_extract_imports(monkeypatch):
    """
    Verifies that the `_extract_imports` method correctly identifies and resolves module imports from a syntax tree.
    
    This test uses a mocked `_resolve_import_path` method to isolate the unit test from file system dependencies, ensuring the test focuses solely on the import extraction logic.
    
    Args:
        monkeypatch: A pytest fixture used to mock the `_resolve_import_path` method to simulate path resolution without file system access.
    
    Returns:
        None: This is a test method and does not return a value.
    """
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
    """
    Tests the resolution of a simple module import with an alias.
    
    Args:
        tmp_path: The temporary path provided by the test fixture for file system operations.
    
    Asserts:
        Verifies that the resolved import correctly identifies the module name and file path while ensuring no specific function is associated with the import. This test ensures that when an import uses an alias, the underlying module and its file path are still correctly resolved, and the function field is appropriately set to None because the import is for the entire module, not a specific function.
    
    Why:
        This test validates that the import resolution logic correctly handles aliased imports, which are common in Python code (e.g., `import mymod as alias`). It confirms that the alias does not interfere with identifying the actual module and its location, and that the resolution does not mistakenly associate a function with a module-level import.
    """
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
    """
    Verifies that the `_resolve_import` method correctly identifies and extracts a function name from a qualified import string.
    
    This test case simulates a scenario where a module is imported and a specific function within that module is called, ensuring the resolver correctly separates the module reference from the function identifier. The test validates that the resolver can parse a qualified name (e.g., "m.do_something") and return the correct function component.
    
    Args:
        None.
    
    Returns:
        None.
    """
    # Arrange
    ts = OSA_TreeSitter(".")
    imports = {"m": {"module": "m", "path": "p"}}

    # Act
    result = ts._resolve_import("m.do_something", "m", imports, {})

    # Assert
    assert result["function"] == "do_something"


def test_resolve_import_class_and_method():
    """
    Verifies that the `_resolve_import` method correctly identifies both the class name and the method call when resolving a complex import string.
    
    This test case specifically checks the scenario where a module member is accessed as an instantiated class followed by a method call (e.g., 'm.MyClass().run'). It ensures the method properly parses the import string to extract the class name and the full method call expression.
    
    Args:
        None explicitly, but the test uses a fixed setup:
        - An instance of OSA_TreeSitter initialized with the current directory.
        - A mock imports dictionary mapping module alias 'm' to its module and path.
        - An empty dictionary for additional context.
    
    Returns:
        None. This is a test method that performs assertions to validate behavior.
    """
    # Arrange
    ts = OSA_TreeSitter(".")
    imports = {"m": {"module": "m", "path": "p"}}

    # Act
    result = ts._resolve_import("m.MyClass().run", "m", imports, {})

    # Assert
    assert result["class"] == "MyClass"
    assert result["function"] == "MyClass().run"


def test_resolve_import_unknown_alias_returns_empty():
    """
    Verifies that resolving an import with an unknown alias returns an empty dictionary.
    
    This test case initializes an OSA_TreeSitter instance and calls the internal _resolve_import method with an alias that does not exist in the provided mappings, asserting that the result is an empty collection. The test ensures that the import resolution logic correctly handles missing or unrecognized aliases by returning an empty result, which prevents erroneous data propagation in the documentation analysis pipeline.
    
    Args:
        None explicitly, but the test internally uses:
            - An OSA_TreeSitter instance configured with a root directory (".").
            - A module path ("x.y") and alias ("x") that are not present in the provided empty mappings.
            - Empty dictionaries for both the module and alias mappings to simulate no known imports.
    
    Returns:
        None
    """
    # Arrange
    ts = OSA_TreeSitter(".")

    # Act
    result = ts._resolve_import("x.y", "x", {}, {})

    # Assert
    assert result == {}


def test_resolve_method_calls_with_assignment():
    """
    Tests the resolution of method calls within an assignment expression.
    
    This test case verifies that the `_resolve_method_calls` method correctly identifies and extracts function names when a method call is part of an assignment statement (e.g., `alias = m.do()`) within a function definition block. It simulates the Tree-sitter node structure for an assignment and checks if the expected module method is returned.
    
    Args:
        No explicit parameters. The test constructs its own Tree-sitter node hierarchy and imports dictionary internally.
    
    Returns:
        None. This is a test method that performs assertions to validate behavior.
    """
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
    """
    Tests the resolution of direct method calls within a function definition.
    
    This test case verifies that the `_resolve_method_calls` method correctly identifies and extracts a direct function call (e.g., 'm.work()') from a syntax tree node, given a set of module imports. It ensures the method returns a list of strings representing the resolved function names.
    
    Args:
        ts: An instance of OSA_TreeSitter initialized with a root directory.
        imports: A dictionary mapping import aliases to module information.
        func_node: A syntax tree node representing an identifier (e.g., 'm.work').
        call_node: A syntax tree node representing a function call, linked to func_node.
        expr: A syntax tree expression node containing the call_node.
        block: A syntax tree block node containing the expression.
        function_node: A syntax tree node representing a function definition, containing the block.
    
    Why:
        This test validates that the internal `_resolve_method_calls` method can parse and resolve method calls from abstract syntax tree (AST) nodes. It is essential for ensuring that the tool correctly extracts function names from code during documentation generation, which supports accurate dependency tracking and API documentation.
    
    Returns:
        None
    """
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
    """
    Verifies that the _resolve_method_calls method returns an empty list when provided with a function node that contains no block or children. This test ensures the method handles edge cases gracefully, preventing errors when encountering minimal or malformed function definitions.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    ts = OSA_TreeSitter(".")
    fn_node = Node("function_definition", children=[])

    # Act
    result = ts._resolve_method_calls(fn_node, "src", {})

    # Assert
    assert result == []


def test_extract_structure_orchestrates(monkeypatch):
    """
    Verifies that the extract_structure method correctly orchestrates the parsing and extraction process.
    
    This test ensures that the OSA_TreeSitter instance properly calls its internal parsing, import extraction, function parsing, and class parsing methods when processing a source file. It uses monkeypatching to mock the tree structure and verify that the respective parsers for functions and classes are triggered.
    
    Args:
        monkeypatch: A pytest fixture used to mock attributes and methods of the OSA_TreeSitter instance.
    
    Why:
        The test validates the orchestration logic of extract_structure, confirming that the method sequentially invokes the necessary internal parsers (_parse_source_code, _extract_imports, _function_parser, _class_parser) when processing a file. This ensures the overall extraction pipeline works as intended without requiring actual file I/O or a full parse tree.
    """
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
    """
    Tests the retrieval of a docstring from a code block node.
    
    This test verifies that the `_get_docstring` method correctly extracts and returns the text content of a docstring when provided with a tree-sitter block node containing an expression statement. It simulates the structure of a Python docstring by creating a mock node hierarchy and asserts that the resulting string matches the expected content.
    
    The test is necessary to ensure the underlying docstring extraction logic works correctly for block nodes, which is a common structure in source code parsing.
    
    Args:
        None.
    
    Returns:
        None.
    """
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
    """
    Tests the `_traverse_block` method of the `OSA_TreeSitter` class to ensure it correctly extracts function details from a code block.
    
    WHY: This test verifies that `_traverse_block` processes a block containing both decorated and non-decorated function definitions, correctly extracting their details and returning them in a list.
    
    Args:
        monkeypatch: A pytest fixture used to mock dependencies and attributes during testing.
    
    Returns:
        None.
    """
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
    result = ts._traverse_block("class_name", block, "code", {})

    # Assert
    assert fake_method in result
    assert len(result) == 2


def test_extract_function_details(monkeypatch):
    """
    Verifies that the `_extract_function_details` method correctly parses a function definition node and extracts its metadata.
    
    This test uses monkeypatching to mock internal helper methods and validates that the resulting dictionary contains the expected method name, arguments, docstring, and resolved method calls. The test constructs a mock function definition node to simulate a real source code function, then checks that the extracted details match the expected structure and content.
    
    Args:
        monkeypatch: A pytest fixture used to mock attributes and methods of the OSA_TreeSitter instance. It is used here to replace `_get_docstring` and `_resolve_method_calls` with controlled return values, ensuring the test isolates the behavior of `_extract_function_details`.
    
    Why this test exists:
        It ensures that the internal parsing logic accurately captures key components of a function—such as its name, parameters, documentation, and any method calls within—which is critical for the tool's documentation generation and code analysis features.
    """
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
    """
    Tests the directory analysis functionality of the OSA_TreeSitter class.
    
    This test verifies that the analyze_directory method correctly identifies files within a given path and processes them using the internal extraction logic. It uses monkeypatching to mock file discovery and structure extraction, ensuring the method returns a result containing the expected file path.
    
    The test creates a temporary Python file, mocks the internal methods to return a controlled file list and a dummy extraction result, and then validates that the file path appears in the analysis results. This isolates the test from actual file system and extraction logic, focusing on the integration of the directory analysis flow.
    
    Args:
        monkeypatch: A pytest fixture used to mock attributes and methods.
        tmp_path: A pytest fixture providing a temporary directory path for file operations.
    """
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
    """
    Verifies that the show_results method correctly logs the structure of parsed files.
    
    This test ensures that the OSA_TreeSitter.show_results method logs the expected formatted output for a given results dictionary, confirming that classes, functions, and their details are properly displayed in the logs.
    
    Args:
        monkeypatch: A pytest fixture used to mock or patch objects, functions, or dictionary items.
        caplog: A pytest fixture used to capture log messages for assertion.
    
    Returns:
        None.
    """
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
    """
    Verifies that the log_results method correctly writes the structural analysis of source code to a report file.
    
    This test ensures that the OSA_TreeSitter.log_results method generates a readable report file containing formatted structural details (such as classes and methods) extracted from the source code analysis.
    
    Args:
        tmp_path: A temporary directory path provided by pytest for file system operations. Used to isolate file creation and cleanup.
        monkeypatch: A pytest fixture used to safely patch attributes and environment variables. Here, it changes the current working directory to the temporary path.
    
    The test performs the following steps:
    1. Sets up an OSA_TreeSitter instance with the temporary directory as the working directory.
    2. Provides a mock analysis results dictionary containing a sample class and method.
    3. Calls log_results to write the report.
    4. Asserts that the report file is created and contains expected formatted content (e.g., "Class: C" and "Method: m").
    5. Cleans up the created report directory after the assertion.
    
    Returns:
        None.
    """
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
