from unittest.mock import MagicMock, AsyncMock, patch

import pytest


@pytest.fixture
def temp_py_file(tmp_path):
    """
    Creates a temporary Python file with simple content.
    
    This method is primarily used for testing purposes, providing a quick way to generate a temporary Python script with predefined content. It writes two simple variable assignments to the file.
    
    Args:
        tmp_path: A path object representing a temporary directory, typically provided by a testing fixture like pytest's `tmp_path`.
    
    Returns:
        The absolute path to the created temporary Python file as a string.
    """
    fpath = tmp_path / "sample.py"
    fpath.write_text("x = 1\ny = 2\n")
    return str(fpath)


@pytest.fixture
def temp_dir_with_files(tmp_path):
    """
    Creates a temporary directory with multiple Python and non-Python files.
    
    This method is used for testing purposes to simulate a directory containing a mix of Python scripts and other file types. It creates two Python files (a.py and b.py) with simple print statements and one non-Python text file (note.txt). The method returns the path to the temporary directory and a list of the Python file paths, allowing tests to verify file handling, filtering, or processing logic that distinguishes between Python and non-Python files.
    
    Args:
        tmp_path: A path object representing a temporary directory where the files will be created.
    
    Returns:
        A tuple containing:
            - The string path of the temporary directory.
            - A list of string paths for the Python files created (a.py and b.py).
    """
    py1 = tmp_path / "a.py"
    py1.write_text("print('a')")

    py2 = tmp_path / "b.py"
    py2.write_text("print('b')")

    txt = tmp_path / "note.txt"
    txt.write_text("not python")

    return str(tmp_path), [str(py1), str(py2)]


@pytest.fixture
def temp_dir_with_ignores(tmp_path):
    """
    Creates a temporary directory structure with files and subdirectories, some of which are intended to be ignored (e.g., by a linter or file scanner). This is useful for testing ignore‑pattern logic in tools that filter files.
    
    Args:
        tmp_path: A temporary directory path (provided by a test fixture like pytest's tmp_path) where the structure will be created.
    
    Returns:
        A tuple containing:
            - The string path of the created temporary directory.
            - A list of string paths to the files that are expected *not* to be ignored (the "allowed" files). In this setup, only 'a.py' and 'allow1/b_allow.py' are considered allowed; all other created files are meant to be ignored.
    """
    (tmp_path / "ignore1").mkdir()
    (tmp_path / "allow1").mkdir()
    (tmp_path / "allow1" / "ignore2").mkdir()

    py1 = tmp_path / "a.py"
    py1.write_text("print('a')")

    ign1 = tmp_path / "ignore1" / "b.py"
    ign1.write_text("print('ignore_b')")

    allow1_init = tmp_path / "allow1" / "__init__.py"
    allow1_init.write_text("print('ignore_init')")

    allow1 = tmp_path / "allow1" / "b_allow.py"
    allow1.write_text("print('b')")

    ign2 = tmp_path / "allow1" / "ignore2" / "c.py"
    ign2.write_text("print('ignore_c')")

    expected_result = [str(tmp_path / "a.py"), str(tmp_path / "allow1" / "b_allow.py")]

    return str(tmp_path), expected_result


class Node:
    """
    Lightweight stub to simulate tree_sitter.Node.
    """


    def __init__(
        self,
        type_,
        text=b"",
        children=None,
        name=None,
        start_point=(0, 0),
        start_byte=0,
        end_byte=0,
        field_function=None,
    ):
        """
        Initializes a new instance of the node with its structural and positional metadata.
        
        Args:
            type_: The category or type of the node (e.g., 'function', 'class', 'call').
            text: The source code text associated with the node; defaults to an empty bytes object.
            children: A list of child nodes; defaults to an empty list if None.
            name: The identifier or name associated with the node; defaults to None.
            start_point: The (row, column) coordinates where the node begins; defaults to (0, 0).
            start_byte: The byte offset where the node begins; defaults to 0.
            end_byte: The byte offset where the node ends; defaults to 0.
            field_function: A function or mapping used specifically for "call" nodes to handle field-related logic; defaults to None.
        
        Attributes:
            type: The category or type of the node.
            text: The source code text associated with the node.
            children: A list of child nodes belonging to this node.
            _name: The internal name or identifier of the node.
            start_point: The (row, column) starting position of the node.
            start_byte: The starting byte index of the node in the source.
            end_byte: The ending byte index of the node in the source.
            field_function: A specific function or logic assigned to "call" nodes, used for processing field information.
        
        Why:
            This constructor sets up a node in a syntax tree, capturing both its content (type, text, children) and its location in the source code (start_point, start_byte, end_byte). The field_function parameter is included to support "call" nodes, which may require special handling for field resolution or mapping, aligning with the tool's goal of detailed source code analysis and documentation.
        """
        self.type = type_
        self.text = text
        self.children = children or []
        self._name = name
        self.start_point = start_point
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.field_function = field_function  # for "call" nodes

    def child_by_field_name(self, field):
        """
        Retrieves a child node or attribute based on a specific field name.
        
        This method provides a structured way to access specific parts of a node's internal representation. It is used to navigate the node's structure by named fields, which correspond to common syntactic elements in code (like function names, parameters, and return types).
        
        Args:
            field: The name of the field to retrieve. Supported values are:
                - "name": Returns a synthetic identifier node containing the node's name (or a default).
                - "parameters": Returns the first child node whose type is "parameters".
                - "return_type": Returns the first child node whose type is "type".
                - "function": Returns the value of the attribute "field_function" if it exists.
        
        Returns:
            Node | None: The corresponding child Node or attribute value if the field is found and valid; otherwise, None. For the "name" field, a new Node object is constructed rather than returning an existing child.
        """
        if field == "name":
            return Node("identifier", text=(self._name or "func").encode())
        if field == "parameters":
            for c in self.children:
                if c.type == "parameters":
                    return c
        if field == "return_type":
            for c in self.children:
                if c.type == "type":
                    return c
        if field == "function":
            return getattr(self, "field_function", None)
        return None


@pytest.fixture
def mock_aiofiles_open():
    """
    Fixture factory for mocking aiofiles.open with custom content.
    
    This factory returns a helper function that creates a unittest.mock.patch object
    to replace aiofiles.open with a mock that simulates asynchronous file operations.
    It is primarily used in testing to avoid actual file I/O and control the content
    returned by read operations.
    
    Args:
        content: The string content that the mocked file's read method will return.
            Defaults to "fake_content".
    
    Returns:
        A callable that, when invoked with optional content, returns a mock.patch
        object configured to replace aiofiles.open. The mocked file supports async
        context manager usage (__aenter__) and provides AsyncMock methods for read
        and write operations.
    
    Why:
        aiofiles provides asynchronous file operations, which require special
        mocking to handle async context managers and coroutines. This fixture
        factory simplifies the creation of consistent mocks for tests that involve
        aiofiles.open, allowing tests to run without real file system dependencies
        and with controllable content.
    """

    def _mock(content: str = "fake_content"):
        mock_file = MagicMock()
        mock_file.__aenter__.return_value.read = AsyncMock(return_value=content)
        mock_file.__aenter__.return_value.write = AsyncMock()
        return patch("aiofiles.open", return_value=mock_file)

    return _mock
