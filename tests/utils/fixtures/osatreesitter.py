from unittest.mock import MagicMock, AsyncMock, patch

import pytest


@pytest.fixture
def temp_py_file(tmp_path):
    """Creates a temporary Python file with simple content."""
    fpath = tmp_path / "sample.py"
    fpath.write_text("x = 1\ny = 2\n")
    return str(fpath)


@pytest.fixture
def temp_dir_with_files(tmp_path):
    """Creates a temporary directory with multiple Python and non-Python files."""
    py1 = tmp_path / "a.py"
    py1.write_text("print('a')")

    py2 = tmp_path / "b.py"
    py2.write_text("print('b')")

    txt = tmp_path / "note.txt"
    txt.write_text("not python")

    return str(tmp_path), [str(py1), str(py2)]

@pytest.fixture
def temp_dir_with_ignores(tmp_path):
    """Creates a temporary directory with multiple to be ignored entities."""
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
    """Lightweight stub to simulate tree_sitter.Node."""

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
        self.type = type_
        self.text = text
        self.children = children or []
        self._name = name
        self.start_point = start_point
        self.start_byte = start_byte
        self.end_byte = end_byte
        self.field_function = field_function  # for "call" nodes

    def child_by_field_name(self, field):
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
    """Fixture factory for mocking aiofiles.open with custom content."""

    def _mock(content: str = "fake_content"):
        mock_file = MagicMock()
        mock_file.__aenter__.return_value.read = AsyncMock(return_value=content)
        mock_file.__aenter__.return_value.write = AsyncMock()
        return patch("aiofiles.open", return_value=mock_file)

    return _mock
