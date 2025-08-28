import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from osa_tool.osatreesitter.docgen import DocGen


def test_format_class(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    class_item = {
        "type": "class",
        "name": "MyClass",
        "start_line": 10,
        "docstring": "This is a class docstring.",
        "methods": [
            {
                "method_name": "my_method",
                "arguments": "self, x",
                "return_type": "int",
                "start_line": 12,
                "docstring": "This is a method docstring.",
                "source_code": "def my_method(self, x): return x",
            }
        ],
    }

    # Act
    result = docgen._format_class(class_item)

    # Assert
    assert "Class: MyClass" in result
    assert "Docstring: This is a class docstring." in result
    assert "Method: my_method" in result
    assert "Args: self, x" in result
    assert "Return: int" in result
    assert "def my_method(self, x): return x" in result


def test_format_function(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    func_item = {
        "type": "function",
        "details": {
            "method_name": "my_func",
            "arguments": "a, b",
            "return_type": "str",
            "start_line": 5,
            "docstring": "Function docstring",
            "source_code": "def my_func(a, b): return str(a+b)",
        },
    }

    # Act
    result = docgen._format_function(func_item)

    # Assert
    assert "Function: my_func" in result
    assert "Args: a, b" in result
    assert "Return: str" in result
    assert "Function docstring" in result
    assert "def my_func(a, b): return str(a+b)" in result


def test_format_structure_openai(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    structure = {
        "file1.py": [
            {"type": "class", "name": "MyClass", "start_line": 1, "docstring": None, "methods": []},
            {
                "type": "function",
                "details": {
                    "method_name": "my_func",
                    "arguments": "",
                    "return_type": "None",
                    "start_line": 5,
                    "docstring": None,
                    "source_code": "def my_func(): pass",
                },
            },
        ]
    }

    # Act
    result = docgen.format_structure_openai(structure)

    # Assert
    assert "File: file1.py" in result
    assert "Class: MyClass" in result
    assert "Function: my_func" in result


def test_format_structure_openai_short_empty(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Act
    result = docgen.format_structure_openai_short("file.py", {"structure": []})

    # Assert
    assert result == ""


def test_format_structure_openai_short_with_content(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    structure = {"structure": [{"type": "class", "name": "Cls", "start_line": 1, "docstring": None, "methods": []}]}

    # Act
    result = docgen.format_structure_openai_short("file.py", structure)

    # Assert
    assert "File: file.py" in result
    assert "Class: Cls" in result


@pytest.mark.parametrize(
    "item,expected",
    [
        (
            {"name": "MyClass", "docstring": "Class docstring.\n\nDetails", "methods": []},
            "  - Class: MyClass\n          Docstring:   Class docstring.\n",
        ),
        ({"name": "NoDocClass", "docstring": None, "methods": []}, "  - Class: NoDocClass\n"),
    ],
)
def test_format_class_short(mock_config_loader, item, expected):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Act
    result = docgen._format_class_short(item)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    "item,expected",
    [
        (
            {
                "details": {
                    "method_name": "my_func",
                    "docstring": "Function docstring.\n\nMore details",
                    "arguments": "",
                    "return_type": "",
                    "start_line": 1,
                    "source_code": "",
                }
            },
            "  - Function: my_func\n          Docstring:\n    Function docstring.\n",
        ),
        (
            {
                "details": {
                    "method_name": "func_no_doc",
                    "docstring": None,
                    "arguments": "",
                    "return_type": "",
                    "start_line": 1,
                    "source_code": "",
                }
            },
            "  - Function: func_no_doc\n",
        ),
    ],
)
def test_format_function_short(mock_config_loader, item, expected):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Act
    result = docgen._format_function_short(item)

    # Assert
    assert result == expected


def test_count_tokens(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    prompt = "Hello world"

    with patch("tiktoken.encoding_for_model") as mock_encoding:
        mock_enc = MagicMock()
        mock_enc.encode.return_value = [0, 1]
        mock_encoding.return_value = mock_enc

        # Act
        count = docgen.count_tokens(prompt)

    # Assert
    assert isinstance(count, int)
    assert count == 2


@pytest.mark.asyncio
async def test_generate_class_documentation(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    docgen.model_handler.async_request = AsyncMock(return_value="Generated docstring")

    class_details = [
        "MyClass",  # class name
        ["attr1", "attr2"],  # attributes
        {"method_name": "foo", "docstring": "Does foo"},  # methods
    ]

    semaphore = asyncio.Semaphore(1)

    # Act
    result = await docgen.generate_class_documentation(class_details, semaphore)

    # Assert
    assert result == "Generated docstring"
    docgen.model_handler.async_request.assert_called_once()


@pytest.mark.asyncio
async def test_update_class_documentation(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    docgen.model_handler.async_request = AsyncMock(return_value="Updated description")
    docgen.main_idea = "Main idea here"

    class_details = ["MyClass", "Other info", "Old description\n\nRest of doc"]

    semaphore = asyncio.Semaphore(1)

    # Act
    result = await docgen.update_class_documentation(class_details, semaphore)

    # Assert
    assert "Updated description" in result
    docgen.model_handler.async_request.assert_called_once()


@pytest.mark.asyncio
async def test_generate_method_documentation(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    docgen.model_handler = MagicMock()
    docgen.model_handler.async_request = AsyncMock(return_value='"""Generated docstring"""')

    method_details = {
        "method_name": "my_method",
        "source_code": "x = 1\nreturn x",
        "arguments": "self",
        "decorators": [],
        "docstring": "",
    }
    semaphore = asyncio.Semaphore(1)

    # Act
    docstring = await docgen.generate_method_documentation(method_details, semaphore)

    # Assert
    assert docstring == '"""Generated docstring"""'
    docgen.model_handler.async_request.assert_called_once()


@pytest.mark.asyncio
async def test_update_method_documentation(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    docgen.main_idea = "This project calculates something important"
    docgen.model_handler = MagicMock()
    docgen.model_handler.async_request = AsyncMock(return_value='"""Updated docstring"""')

    method_details = {
        "method_name": "my_method",
        "source_code": "x = 1\nreturn x",
        "arguments": "self",
        "decorators": [],
        "docstring": '"""Old docstring"""',
    }
    semaphore = asyncio.Semaphore(1)

    # Act
    updated_doc = await docgen.update_method_documentation(method_details, semaphore)

    # Assert
    assert updated_doc == '"""Updated docstring"""'
    docgen.model_handler.async_request.assert_called_once()


def test_valid_triple_quotes(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = '"""\nThis is a test docstring.\n"""'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == resp


def test_with_triple_quotes_placeholder(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = "<triple quotes>\nSome content\n<triple quotes>"

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == '"""\nSome content\n"""'


def test_with_markdown_code_block(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = '```python\n"""\nInside code block\n"""\n```'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == '"""\nInside code block\n"""'


def test_unclosed_triple_quotes_fixed(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = '"""\nUnclosed docstring without ending'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result.startswith('"""')
    assert result.endswith('"""')


def test_remove_def_leakage(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = '"""\ndef some_func():\n    Actual docs\n"""'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert "def some_func" not in result
    assert "Actual docs" in result


def test_fix_indented_args(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = '"""\nDescription.\n    Args:\n        param: something\n"""'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert "Args:" in result
    assert "    Args" not in result  # indentation removed


def test_single_quotes_docstring(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = "'''\nAnother doc\n'''"

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == "'''\nAnother doc\n'''"


def test_fallback_when_no_quotes(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = "This looks like a long enough text without quotes to be treated as docstring"

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result.startswith('"""')
    assert result.endswith('"""')


def test_invalid_short_response(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    resp = "Hi"

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == '"""No valid docstring found."""'


@pytest.mark.parametrize(
    "body, expected",
    [
        (
            '"""One line docstring"""\nprint("hello")',
            'print("hello")',
        ),
        (
            '"""\nThis is a long\nmultiline docstring\n"""\nprint("world")',
            'print("world")',
        ),
        (
            'print("no docs")',
            'print("no docs")',
        ),
        (
            "",
            "",
        ),
        (
            "'''\nAlt docstring\n'''\nprint(123)",
            "print(123)",
        ),
    ],
)
def test_strip_docstring_from_body(mock_config_loader, body, expected):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Act
    result = docgen.strip_docstring_from_body(body)

    # Assert
    assert result.strip() == expected.strip()


@pytest.mark.parametrize(
    "source, method_details, new_doc, expected_snippet",
    [
        (
            "def foo(x):\n    return x + 1\n",
            {"source_code": "def foo(x):\n    return x + 1\n"},
            '"""Adds one"""',
            '"""Adds one"""',
        ),
        (
            'def bar(y):\n    """Old doc"""\n    return y * 2\n',
            {"source_code": 'def bar(y):\n    """Old doc"""\n    return y * 2\n'},
            '"""Multiply by two"""',
            '"""Multiply by two"""',
        ),
        (
            "async def baz(z):\n    return z - 1\n",
            {"source_code": "async def baz(z):\n    return z - 1\n"},
            '"""Subtract one"""',
            '"""Subtract one"""',
        ),
    ],
)
def test_insert_docstring_in_code(mock_config_loader, source, method_details, new_doc, expected_snippet):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Act
    updated = docgen.insert_docstring_in_code(source, method_details, new_doc)

    # Assert
    assert updated == source


@pytest.mark.parametrize(
    "source, class_name, new_doc, expected_snippet",
    [
        (
            "class MyClass:\n    pass\n",
            "MyClass",
            '"""This is a class"""',
            '"""\n    This is a class\n    """',
        ),
        (
            'class OldClass:\n    """Old docstring"""\n    pass\n',
            "OldClass",
            '"""Updated docstring"""',
            '"""\n    Updated docstring\n    """',
        ),
        (
            "class ParamClass(Base):\n    pass\n",
            "ParamClass",
            '"""Class with base"""',
            '"""\n    Class with base\n    """',
        ),
    ],
)
def test_insert_cls_docstring_in_code(mock_config_loader, source, class_name, new_doc, expected_snippet):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Act
    updated = docgen.insert_cls_docstring_in_code(source, class_name, new_doc)

    # Assert
    assert expected_snippet in updated


@pytest.mark.parametrize(
    "method_details, structure, expected",
    [
        (
            {"method_calls": [{"path": "file1.py", "class": "MyClass", "function": "foo"}]},
            {
                "file1.py": {
                    "structure": [
                        {
                            "type": "class",
                            "name": "MyClass",
                            "methods": [{"method_name": "foo", "source_code": "def foo(self): pass"}],
                        }
                    ]
                }
            },
            "# Method foo in class MyClass\ndef foo(self): pass",
        ),
        (
            {"method_calls": [{"path": "file2.py", "class": "InitClass", "function": None}]},
            {
                "file2.py": {
                    "structure": [
                        {
                            "type": "class",
                            "name": "InitClass",
                            "methods": [{"method_name": "__init__", "source_code": "def __init__(self): pass"}],
                        }
                    ]
                }
            },
            "# Method __init__ in class InitClass\ndef __init__(self): pass",
        ),
        (
            {"method_calls": [{"path": "file3.py", "class": "standalone_func", "function": None}]},
            {
                "file3.py": {
                    "structure": [
                        {
                            "type": "function",
                            "details": {"method_name": "standalone_func", "source_code": "def standalone_func(): pass"},
                        }
                    ]
                }
            },
            "# Function standalone_func\ndef standalone_func(): pass",
        ),
        (
            {"method_calls": [{"path": "missing.py", "class": "X", "function": "y"}]},
            {},
            "",
        ),
    ],
)
def test_context_extractor(mock_config_loader, method_details, structure, expected):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Act
    result = docgen.context_extractor(method_details, structure)

    # Assert
    assert result.strip() == expected.strip()


def test_format_with_black_calls_black(mock_config_loader, tmp_path):
    # Arrange
    docgen = DocGen(mock_config_loader)
    test_file = tmp_path / "test.py"
    test_file.write_text("x=1")

    with patch("black.format_file_in_place") as mock_format:
        # Act
        docgen.format_with_black(str(test_file))

    # Assert
    mock_format.assert_called_once()
    called_args = mock_format.call_args[0][0]
    assert isinstance(called_args, Path)
    assert str(called_args).endswith("test.py")


@pytest.mark.asyncio
async def test_generate_the_main_idea_filters_and_sorts(mock_config_loader, mocker):
    # Arrange
    docgen = DocGen(mock_config_loader)
    mock_request = mocker.AsyncMock(return_value="# Project\n## Overview\n## Purpose")
    docgen.model_handler.async_request = mock_request

    parsed_structure = {
        "src/core.py": {
            "imports": ["os", "sys", "re"],
            "structure": [
                {"type": "class", "name": "Core", "docstring": "Main core class"},
                {"type": "function", "details": {"method_name": "run", "docstring": "Run system"}},
            ],
        },
        "src/utils.py": {
            "imports": ["os"],
            "structure": [{"type": "function", "details": {"method_name": "helper", "docstring": "Helper func"}}],
        },
        "tests/test_core.py": {
            "imports": ["pytest"],
            "structure": [],
        },
    }

    # Act
    await docgen.generate_the_main_idea(parsed_structure, top_n=1)

    # Assert
    assert "# Project" in docgen.main_idea

    mock_request.assert_called_once()
    called_prompt = mock_request.call_args[0][0]
    assert "Core" in called_prompt
    assert "helper" not in called_prompt
    assert "tests/test_core.py" not in called_prompt


@pytest.mark.asyncio
async def test_summarize_submodules_creates_summaries(mock_config_loader, mocker, tmp_path):
    # Arrange
    docgen = DocGen(mock_config_loader)
    docgen.config.git.name = str(tmp_path)

    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("")
    (pkg_dir / "core.py").write_text("def run(): pass")

    sub_dir = pkg_dir / "sub"
    sub_dir.mkdir()
    (sub_dir / "__init__.py").write_text("")
    (sub_dir / "helper.py").write_text("def helper(): pass")

    mocker.patch.object(docgen.model_handler, "async_request", new=mocker.AsyncMock(return_value="Summary of module"))

    project_structure = {
        str(pkg_dir / "core.py"): {
            "structure": [{"name": "run", "type": "function", "details": {"method_name": "run", "docstring": None}}]
        },
        str(sub_dir / "helper.py"): {
            "structure": [
                {"name": "helper", "type": "function", "details": {"method_name": "helper", "docstring": None}}
            ]
        },
    }

    # Act
    summaries = await docgen.summarize_submodules(project_structure)

    # Assert
    assert summaries[str(pkg_dir)] == "Summary of module"
    assert summaries[str(sub_dir)] == "Summary of module"


def test_convert_path_to_dot_notation(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Assert
    assert docgen.convert_path_to_dot_notation("a/b/c.py") == "::: a.b.c"
    assert docgen.convert_path_to_dot_notation("a/__init__.py") == "::: a"
    assert docgen.convert_path_to_dot_notation(Path("x/y/z.py")) == "::: x.y.z"


@patch("osa_tool.osatreesitter.docgen.Path.mkdir")
@patch("osa_tool.osatreesitter.docgen.Path.write_text")
@patch("osa_tool.osatreesitter.docgen.shutil.copy")
@patch("osa_tool.osatreesitter.docgen.osa_project_root")
def test_generate_documentation_mkdocs(mock_root, mock_copy, mock_write_text, mock_mkdir, mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    mock_root.return_value = Path("/fake/project")

    files_info = {
        "src/module1.py": {"structure": True},
        "src/module2.py": {"structure": False},
    }
    modules_info = {"src/module1": "Module 1 documentation"}

    with patch("osa_tool.osatreesitter.docgen.logger") as mock_logger:
        # Act
        docgen.generate_documentation_mkdocs("src", files_info, modules_info)

    # Assert
    assert mock_mkdir.called
    assert mock_write_text.called
    mock_copy.assert_called_once()


def test_sanitize_name_basic(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)

    # Assert
    assert docgen._sanitize_name("valid_name") == "valid_name"
    assert docgen._sanitize_name("name.with.dots") == "name_with_dots"
    assert docgen._sanitize_name("1starts_with_digit") == "v1starts_with_digit"
    assert docgen._sanitize_name(".hidden") == "v.hidden".replace(".", "_")


def test_rename_invalid_dirs(mock_config_loader, tmp_path):
    # Arrange
    docgen = DocGen(mock_config_loader)
    invalid_dir = tmp_path / "1invalid"
    invalid_dir.mkdir()
    valid_dir = tmp_path / "valid"
    valid_dir.mkdir()

    # act
    docgen._rename_invalid_dirs(tmp_path)

    # Assert
    assert (tmp_path / "v1invalid").exists()
    assert (tmp_path / "valid").exists()


def test_add_init_files_creates_inits(mock_config_loader, tmp_path):
    # Arrange
    docgen = DocGen(mock_config_loader)

    subdir = tmp_path / "package"
    subdir.mkdir()
    py_file = subdir / "module.py"
    py_file.touch()

    # Act
    docgen._add_init_files(tmp_path)

    # Assert
    assert (subdir / "__init__.py").exists()


def test_purge_temp_files_removes_temp_dir(mock_config_loader, tmp_path):
    # Arrange
    docgen = DocGen(mock_config_loader)

    temp_dir = tmp_path / "mkdocs_temp"
    temp_dir.mkdir()
    (temp_dir / "file.txt").touch()

    # Assert
    assert temp_dir.exists()
    docgen._purge_temp_files(tmp_path)
    assert not temp_dir.exists()


@pytest.mark.asyncio
async def test_generate_docstrings_for_functions_methods(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)

    async def mock_fetch_docstrings(filename, structure, parsed_structure, semaphore):
        return {"functions": [("docstring", "func1")], "methods": [("docstring", "method1")]}

    docgen._fetch_docstrings = mock_fetch_docstrings
    parsed_structure = {
        "file1.py": {"structure": True},
        "file2.py": {"structure": True},
    }

    # Act
    results = await docgen._generate_docstrings_for_items(parsed_structure, ("functions", "methods"))

    # Assert
    for file in parsed_structure:
        assert "functions" in results[file]
        assert "methods" in results[file]


@pytest.mark.asyncio
async def test_generate_docstrings_for_classes(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)

    async def mock_fetch_docstrings_for_class(filename, structure, semaphore):
        return {"classes": [("docstring", "Class1")]}

    docgen._fetch_docstrings_for_class = mock_fetch_docstrings_for_class
    parsed_structure = {
        "file1.py": {"structure": True},
        "file2.py": {"structure": True},
    }

    # Act
    results = await docgen._generate_docstrings_for_items(parsed_structure, "classes")

    # Assert
    for file in parsed_structure:
        assert "classes" in results[file]


@pytest.mark.asyncio
async def test_generate_docstrings_for_all_types(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)

    async def mock_fetch_docstrings(filename, structure, parsed_structure, semaphore):
        return {"functions": [("docstring", "func1")], "methods": [("docstring", "method1")]}

    async def mock_fetch_docstrings_for_class(filename, structure, semaphore):
        return {"classes": [("docstring", "Class1")]}

    docgen._fetch_docstrings = mock_fetch_docstrings
    docgen._fetch_docstrings_for_class = mock_fetch_docstrings_for_class
    parsed_structure = {
        "file1.py": {"structure": True},
        "file2.py": {"structure": True},
    }

    # Act
    results = await docgen._generate_docstrings_for_items(parsed_structure, ("functions", "methods", "classes"))

    # Assert
    for file in parsed_structure:
        assert "functions" in results[file]
        assert "methods" in results[file]
        assert "classes" in results[file]


def test_perform_code_augmentations(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    with (
        patch("osa_tool.osatreesitter.docgen.DocGen.insert_docstring_in_code") as mock_insert,
        patch("osa_tool.osatreesitter.docgen.DocGen.insert_cls_docstring_in_code") as mock_insert_cls,
    ):
        mock_insert.side_effect = lambda src, obj, doc, class_method=False: src + f"\n# {doc}"
        mock_insert_cls.side_effect = lambda src, cls, doc: src + f"\n# {doc}"

        args = ("file1.py", "def foo(): pass", {"functions": [("doc1", "foo")], "methods": [], "classes": []})

        # Act
        result = docgen._perform_code_augmentations(args)

        # Assert
        assert "file1.py" in result
        assert "# doc1" in result["file1.py"]


def test_run_in_executor_with_fake_augment(mock_config_loader):
    # Arrange
    docgen = DocGen(mock_config_loader)
    parsed_structure = {
        "file1.py": {"structure": True},
        "file2.py": {"structure": True},
    }
    project_source_code = {
        "file1.py": "def foo(): pass",
        "file2.py": "def bar(): pass",
    }
    generated_docstrings = {
        "file1.py": {"functions": [("doc1", "foo")], "methods": [], "classes": []},
        "file2.py": {"functions": [("doc2", "bar")], "methods": [], "classes": []},
    }

    def fake_augment(args):
        filename, src, docs = args
        return {filename: src + "\n# augmented"}

    # Act
    args = [(file, project_source_code[file], generated_docstrings[file]) for file in parsed_structure]
    results = []
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=2) as executor:
        for result in executor.map(fake_augment, args):
            results.append(result)

    # Assert
    expected_results = [
        {"file1.py": "def foo(): pass\n# augmented"},
        {"file2.py": "def bar(): pass\n# augmented"},
    ]
    assert results == expected_results


@pytest.mark.asyncio
async def test_get_project_source_code_with_config(tmp_path, mock_config_loader):
    # Arrange
    files = {"file1.py": "print('hello')", "file2.py": "print('world')"}

    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    parsed_structure = {str(tmp_path / name): {"structure": True} for name in files}

    sem = asyncio.Semaphore(2)

    docgen = DocGen(config_loader=mock_config_loader)

    # Act
    result = await docgen._get_project_source_code(parsed_structure, sem)

    # Assert
    expected = {str(tmp_path / k): v for k, v in files.items()}
    assert result == expected


@pytest.mark.asyncio
async def test_write_augmented_code_with_config(tmp_path, mock_config_loader):
    # Arrange
    files = ["file1.py", "file2.py"]
    for f in files:
        (tmp_path / f).write_text("old code", encoding="utf-8")
    parsed_structure = {str(tmp_path / f): {"structure": True} for f in files}
    augmented_code = [{str(tmp_path / files[0]): "new code 1"}, {str(tmp_path / files[1]): "new code 2"}]

    sem = asyncio.Semaphore(2)
    docgen = DocGen(config_loader=mock_config_loader)

    # Act
    await docgen._write_augmented_code(parsed_structure, augmented_code, sem)

    # Assert
    for i, f in enumerate(files):
        content = (tmp_path / f).read_text(encoding="utf-8")
        assert content == augmented_code[i][str(tmp_path / f)]
