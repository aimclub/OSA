import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from osa_tool.operations.codebase.docstring_generation.docgen import DocGen


def test_format_class(mock_config_manager):
    """
    Tests the formatting of class information by the DocGen class.
    
    This test case verifies that the `_format_class` method correctly processes a class metadata dictionary—including its name, docstring, and nested method details—and returns a formatted string containing all the expected information.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object. This fixture is provided by the test framework (e.g., pytest).
    
    Why:
        This test ensures the documentation generator formats class data correctly, which is essential for producing accurate and complete API documentation from source code analysis.
    
    The test:
        1. Creates a DocGen instance using the mocked configuration manager.
        2. Defines a sample class metadata dictionary containing a class name, docstring, start line, and a list of method details.
        3. Calls the `_format_class` method with this dictionary.
        4. Asserts that the returned formatted string contains specific expected substrings, verifying the proper inclusion of the class name, class docstring, method name, method arguments, return type, and method source code.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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


def test_format_function(mock_config_manager):
    """
    Verifies that the `_format_function` method of the `DocGen` class correctly formats function metadata into a string representation.
    
    This test case simulates a function item containing details such as the method name, arguments, return type, docstring, and source code, then asserts that the resulting formatted string contains all the expected information. The test ensures the formatting logic properly extracts and presents each piece of metadata.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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


def test_format_structure_openai(mock_config_manager):
    """
    Verifies that the format_structure_openai method correctly converts a file structure dictionary into a formatted string for OpenAI.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object. This fixture provides a controlled configuration environment for isolated testing.
    
    Why:
        This test ensures the formatting logic produces a readable, structured string representation suitable for OpenAI's processing, which is a key step in automated documentation generation. It validates that classes, functions, and file names are properly labeled and included in the output.
    
    Returns:
        None. This is a test method; it uses assertions to verify behavior and does not return a value.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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


def test_format_structure_openai_short_empty(mock_config_manager):
    """
    Verifies that the format_structure_openai_short method returns an empty string when provided with an empty structure list.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object. This fixture ensures the test does not depend on real configuration.
    
    Why:
        This test ensures the method handles edge cases correctly—specifically, that an empty structure list produces an empty output string, preventing unexpected formatting or errors in downstream documentation processes.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    # Act
    result = docgen.format_structure_openai_short("file.py", {"structure": []})

    # Assert
    assert result == ""


def test_format_structure_openai_short_with_content(mock_config_manager):
    """
    Verifies that the format_structure_openai_short method correctly formats a file structure containing a class into a string representation for OpenAI.
    
    This test ensures the method produces a readable, structured string output suitable for OpenAI consumption, specifically checking that file and class names are properly included in the formatted result.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
def test_format_class_short(mock_config_manager, item, expected):
    """
    Verifies that the `_format_class_short` method correctly formats class information into a condensed string representation.
    
    This test ensures the method produces the expected string output for various class metadata inputs, validating the formatting logic for class names, docstrings, and method lists.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object, isolating the test from external configuration dependencies.
        item: A dictionary containing class metadata to be formatted. Expected keys include 'name' (the class name), 'docstring' (the class documentation, which may be None), and 'methods' (a list of methods, though the test currently uses empty lists).
        expected: The expected string output representing the formatted class details, used to verify the method's correctness.
    
    The test follows a standard Arrange-Act-Assert pattern: it creates a DocGen instance, calls `_format_class_short` with the provided item, and asserts the result matches the expected output.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

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
def test_format_function_short(mock_config_manager, item, expected):
    """
    Tests the short formatting of function details using various input scenarios.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize DocGen.
        item: A dictionary containing function metadata. The dictionary must have a "details" key, which itself is a dictionary containing:
            - method_name: The name of the function.
            - docstring: The function's docstring text, or None if absent.
            - arguments: A string representation of the function's arguments.
            - return_type: A string representation of the function's return type.
            - start_line: The line number where the function starts in the source.
            - source_code: The raw source code of the function.
        expected: The expected formatted string output to assert against.
    
    Returns:
        None.
    
    Why:
        This test validates the `_format_function_short` method of DocGen, ensuring it correctly formats function metadata into a concise, readable string for documentation purposes. It specifically checks handling of both functions with and without docstrings.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    # Act
    result = docgen._format_function_short(item)

    # Assert
    assert result == expected


def test_count_tokens(mock_config_manager):
    """
    Verifies that the count_tokens method correctly calculates the number of tokens in a string.
    
    This test mocks the tiktoken encoding process to ensure that the DocGen instance correctly interacts with the encoding library and returns the expected integer count based on the length of the encoded token list. The test uses a fixed prompt ("Hello world") and a mocked encoding that returns a list of two tokens to validate that the method returns the correct count (2) and that the result is an integer.
    
    Args:
        mock_config_manager: A mocked configuration manager used to initialize the DocGen instance.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
async def test_generate_class_documentation(mock_config_manager):
    """
    Asynchronously tests the `generate_class_documentation` method of the `DocGen` class.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Why:
        This test verifies that `generate_class_documentation` correctly interacts with the model handler to produce documentation for a given class. It ensures the method properly structures the request and returns the generated docstring.
    
    Details:
        The test sets up a DocGen instance with a mocked async_request that returns a fixed string. It then provides sample class details (name, attributes, and methods) and a semaphore to control concurrency. After calling the method, it asserts that the returned result matches the mocked response and that the model handler was called exactly once.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
async def test_update_class_documentation(mock_config_manager):
    """
    Asynchronously tests the update_class_documentation method of the DocGen class.
    
    Args:
        mock_config_manager: A mocked configuration manager used to initialize the DocGen instance.
    
    WHY: This test verifies that the DocGen.update_class_documentation method correctly updates a class's documentation by calling the model handler and incorporating the main idea. It ensures the method integrates with asynchronous processing via a semaphore and returns the updated documentation string.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
async def test_generate_method_documentation(mock_config_manager):
    """
    Tests the generation of method documentation by mocking the model handler and verifying the output.
    
    This test ensures that the `generate_method_documentation` method correctly interacts with the mocked model handler to produce a docstring. It validates that the method formats the request properly and returns the expected result.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None: This is a test method and does not return a value.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
    assert docstring == "Generated docstring"
    docgen.model_handler.async_request.assert_called_once()


@pytest.mark.asyncio
async def test_update_method_documentation(mock_config_manager):
    """
    Asynchronously tests the `update_method_documentation` method of the DocGen class.
    
    Args:
        mock_config_manager: A mocked configuration manager used to initialize the DocGen instance.
    
    WHY: This test verifies that the DocGen instance correctly updates a method's docstring by interacting with a mocked AI model handler. It ensures the method processes the input details, respects concurrency controls via a semaphore, and returns the updated documentation as expected.
    
    The test follows an Arrange-Act-Assert pattern:
    1. Arrange: Creates a DocGen instance with a mocked model handler, sets up method details and a semaphore.
    2. Act: Calls `update_method_documentation` with the method details and semaphore.
    3. Assert: Checks that the returned docstring matches the expected updated value and that the model handler was called exactly once.
    
    Note: This is a test method and does not return a value.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
    assert updated_doc == "Updated docstring"
    docgen.model_handler.async_request.assert_called_once()


def test_valid_triple_quotes(mock_config_manager):
    """
    Verifies that the extract_pure_docstring method correctly handles and returns a valid triple-quoted docstring.
    
    This test ensures the method properly extracts a docstring when the input is already a clean, triple-quoted string without any surrounding text or code. It is important because the method must reliably identify and return pure docstrings in isolation, which is a common case when processing well‑formed documentation responses.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    resp = '"""\nThis is a test docstring.\n"""'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == resp


def test_with_triple_quotes_placeholder(mock_config_manager):
    """
    Verifies that the extract_pure_docstring method correctly replaces placeholder tags with actual triple quotes.
    
    WHY: This test ensures that the method properly handles a common placeholder format used in generated documentation, converting it to a standard Python docstring format.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    resp = "<triple quotes>\nSome content\n<triple quotes>"

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == '"""\nSome content\n"""'


def test_with_markdown_code_block(mock_config_manager):
    """
    Verifies that the docstring extraction logic correctly handles and strips Markdown code block delimiters.
    This test ensures that when a response contains a Markdown code block (e.g., ```python), the extraction method removes the block delimiters while preserving the inner content, which is essential for clean docstring processing.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    resp = '```python\n"""\nInside code block\n"""\n```'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == '"""\nInside code block\n"""'


def test_unclosed_triple_quotes_fixed(mock_config_manager):
    """
    Verifies that the docstring extraction logic correctly fixes and closes unclosed triple quotes by ensuring the extracted result is properly wrapped in triple quotes.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object. This provides the necessary configuration for the DocGen instance to operate in a controlled test environment.
    
    Why:
        This test ensures the robustness of the docstring extraction process when handling incomplete or malformed input. It validates that the extraction method automatically corrects unclosed triple‑quoted strings, which is essential for generating syntactically valid docstrings in the automated documentation pipeline.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    resp = '"""\nUnclosed docstring without ending'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result.startswith('"""')
    assert result.endswith('"""')


def test_remove_def_leakage(mock_config_manager):
    """
    Verifies that the docstring extraction process correctly removes leaked function definitions from the LLM response.
    
    This test ensures that when an LLM response inadvertently includes a function definition (e.g., 'def some_func():') within the docstring text, the extraction method filters it out, leaving only the intended documentation content.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    resp = '"""\ndef some_func():\n    Actual docs\n"""'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert "def some_func" not in result
    assert "Actual docs" in result


def test_fix_indented_args(mock_config_manager):
    """
    Verifies that the docstring extraction logic correctly removes leading indentation from the 'Args' section of a generated docstring.
    
    This test ensures that when a docstring is generated with an indented 'Args' block, the extraction process normalizes the formatting by stripping the extra leading whitespace, which is important for consistent documentation output and readability.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    resp = '"""\nDescription.\n    Args:\n        param: something\n"""'

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert "Args:" in result
    assert "    Args" not in result  # indentation removed


def test_single_quotes_docstring(mock_config_manager):
    """
    Verifies that the extract_pure_docstring method correctly handles and preserves docstrings wrapped in single triple quotes.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Why:
        This test ensures that docstrings formatted with single triple quotes (''')—as opposed to the more common double triple quotes (
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    resp = "'''\nAnother doc\n'''"

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result == "'''\nAnother doc\n'''"


def test_fallback_when_no_quotes(mock_config_manager):
    """
    Verifies that the docstring extraction logic correctly falls back to treating the entire response as a docstring when no quotes are present.
    This test ensures that when the provided response string lacks any quotation marks, the extraction method wraps the entire input as a triple-quoted docstring.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    resp = "This looks like a long enough text without quotes to be treated as docstring"

    # Act
    result = docgen.extract_pure_docstring(resp)

    # Assert
    assert result.startswith('"""')
    assert result.endswith('"""')


def test_invalid_short_response(mock_config_manager):
    """
    Verifies that the docstring extraction logic handles short, invalid responses correctly.
    
    This test case ensures that when the LLM provides a response that is too short or does not contain a valid docstring structure, the system returns a default fallback message.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Why:
        This test validates the robustness of the extraction logic against malformed or insufficient input, ensuring a predictable default output instead of an error or empty result.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
def test_strip_docstring_from_body(mock_config_manager, body, expected):
    """
    Verifies that the strip_docstring_from_body method correctly removes leading docstrings from a given code block.
    
    This test ensures the method handles various docstring formats (single-line, multi-line, triple-single-quotes, triple-double-quotes) and edge cases (no docstring, empty input) as expected.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
        body: The source code string containing an optional docstring to be stripped.
        expected: The expected source code string after the docstring has been removed.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

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
def test_insert_docstring_in_code(mock_config_manager, source, method_details, new_doc, expected_snippet):
    """
    Verifies that the `insert_docstring_in_code` method correctly inserts or replaces docstrings within various source code snippets.
    
    This test uses parameterized inputs to validate that the `DocGen` class can handle standard function definitions, functions with existing docstrings, and asynchronous function definitions. The test ensures the method updates the source code as expected, maintaining the original code structure while inserting or replacing the docstring.
    
    Args:
        mock_config_manager: A mocked configuration manager instance required to initialize DocGen.
        source: The original source code string of the method. This is the input to the method being tested.
        method_details: A dictionary containing metadata about the method, specifically the 'source_code' key. It is passed to the method but is not used in the test's assertion, as the test compares the result directly to the original source.
        new_doc: The new docstring content to be inserted or used as a replacement.
        expected_snippet: The expected resulting source code after the docstring insertion. In the provided test cases, this is identical to the original source, indicating the test currently validates that the method returns the input unchanged.
    
    Why:
        The test is designed to verify the behavior of `insert_docstring_in_code` under different scenarios. However, the current implementation of the test expects the method to return the source unchanged (since `updated == source` is asserted). This suggests the test may be incomplete or the method's intended functionality is not yet implemented, as the parameterized examples include new docstrings that are not actually inserted. The docstring should reflect the test's actual verification logic.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

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
def test_insert_cls_docstring_in_code(mock_config_manager, source, class_name, new_doc, expected_snippet):
    """
    Verifies that the class-level docstring is correctly inserted or updated within a source code string.
    
    This test case uses parametrization to check various scenarios, including classes without existing docstrings, classes with existing docstrings that need replacement, and classes that inherit from base classes. It ensures that the formatting and indentation of the new docstring are handled correctly by the DocGen utility.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize DocGen.
        source: The original source code string containing the class definition.
        class_name: The name of the class within the source code to target.
        new_doc: The raw docstring content to be inserted. This is the literal docstring text, including triple quotes, that will be placed into the class.
        expected_snippet: The expected formatted string that should appear in the updated source code. This is used to verify the docstring is inserted with correct indentation and line breaks.
    
    Why:
        This test validates the core functionality of the DocGen utility's `insert_cls_docstring_in_code` method. It is important to ensure the utility can handle different class definitions (with/without existing docstrings, with inheritance) and correctly format the new docstring according to Python conventions, preserving the surrounding code structure.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    # Act
    updated = docgen.insert_cls_docstring_in_code(source, class_name, new_doc)

    # Assert
    assert expected_snippet in updated


@pytest.mark.parametrize(
    "method_details, function_index, expected_contains",
    [
        (
            {"method_calls": ["foo"]},
            {"foo": {"method_name": "foo", "docstring": "Does foo", "file": "file1.py", "class": "MyClass"}},
            "MyClass.foo",
        ),
        (
            {"method_calls": ["helper"]},
            {"helper": {"method_name": "helper", "docstring": "Helper func", "file": "file2.py"}},
            "helper",
        ),
        (
            {"method_calls": ["unknown"]},
            {},
            "",
        ),
        (
            {"method_calls": []},
            {"foo": {"method_name": "foo", "docstring": "Does foo"}},
            "",
        ),
    ],
)
def test_context_extractor(mock_config_manager, method_details, function_index, expected_contains):
    """
    Verifies that the context_extractor method correctly identifies and formats information about called functions based on the provided method details and function index.
    
    This test ensures that the DocGen.context_extractor method properly processes a list of called function names (method_calls) by looking them up in a function index. It validates that the extracted context string contains the expected formatted output (e.g., "MyClass.foo" or "helper") or is empty when no calls are present or a function is not found.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
        method_details: A dictionary containing details about the method being tested. Must include a 'method_calls' key with a list of function names to look up.
        function_index: A dictionary mapping function names to their metadata (e.g., name, docstring, file, class). Used to retrieve information for each called function.
        expected_contains: The expected substring that should appear in the extracted context result. If empty string, the test expects the result to also be empty.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    # Act
    result = docgen.context_extractor(method_details, {}, function_index=function_index)

    # Assert
    if expected_contains:
        assert expected_contains in result
    else:
        assert result == ""


def test_format_with_black_calls_black(mock_config_manager, tmp_path):
    """
    Verifies that the `format_with_black` method correctly invokes the underlying `black.format_file_in_place` function.
    
    This test ensures that when a file path is provided to the `DocGen` instance, it properly delegates the formatting task to the Black library with the expected file path argument. The test uses mocking to isolate the call and verify the correct argument is passed.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize DocGen.
        tmp_path: A pytest fixture providing a temporary directory path for creating test files.
    
    Why:
        This test confirms that the `DocGen.format_with_black` method correctly integrates with the Black formatting library by ensuring the underlying `black.format_file_in_place` function is called exactly once with the intended file path. This validation is important to guarantee that the formatting delegation works as designed without unintended side effects or incorrect arguments.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
async def test_generate_the_main_idea_filters_and_sorts(mock_config_manager, mocker):
    """
    Verifies that the main idea generation correctly filters and sorts the project structure.
    
    This test ensures that the `generate_the_main_idea` method prioritizes and includes only the most relevant source files and components (based on the `top_n` parameter) while excluding less relevant items like utility functions and test files. It validates that the generated prompt sent to the model handler focuses on core project elements.
    
    Args:
        mock_config_manager: A mocked configuration manager instance.
        mocker: The pytest-mock fixture for creating mocks and spies.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
async def test_summarize_submodules_creates_summaries(mock_config_manager, mocker, tmp_path):
    """
    Verifies that the summarize_submodules method correctly generates summaries for directories within a project structure.
    
    This test case sets up a mock package structure with nested directories and files, mocks the model handler's asynchronous request to return a predefined summary, and asserts that the resulting summaries dictionary contains the expected entries for each submodule directory.
    
    Args:
        mock_config_manager: A mock object for managing configuration settings.
        mocker: The pytest-mocker fixture used for patching and mocking objects.
        tmp_path: A pytest fixture providing a temporary directory path for file system operations.
    
    Why:
        This test ensures that the DocGen.summarize_submodules method properly processes a project structure dictionary, groups files by their parent directories, and requests a summary for each directory. It validates that the method correctly maps directory paths to generated summaries, which is essential for creating hierarchical documentation.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    docgen.config_manager.config.git.name = str(tmp_path)

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


def test_convert_path_to_dot_notation(mock_config_manager):
    """
    Verifies that the `convert_path_to_dot_notation` method correctly transforms file paths into MkDocs-style dot notation strings.
    This test ensures the method handles both string and Path object inputs, properly converts directory separators to dots, and correctly treats `__init__.py` files as representing their parent package.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    # Assert
    assert docgen.convert_path_to_dot_notation("a/b/c.py") == "::: a.b.c"
    assert docgen.convert_path_to_dot_notation("a/__init__.py") == "::: a"
    assert docgen.convert_path_to_dot_notation(Path("x/y/z.py")) == "::: x.y.z"


@patch("osa_tool.operations.codebase.docstring_generation.docgen.Path.mkdir")
@patch("osa_tool.operations.codebase.docstring_generation.docgen.Path.write_text")
@patch("osa_tool.operations.codebase.docstring_generation.docgen.shutil.copy")
@patch("osa_tool.operations.codebase.docstring_generation.docgen.osa_project_root")
def test_generate_documentation_mkdocs(mock_root, mock_copy, mock_write_text, mock_mkdir, mock_config_manager):
    """
    Verifies that the generate_documentation_mkdocs method correctly triggers directory creation, file writing, and asset copying.
    
    This test ensures the method orchestrates the necessary filesystem operations to build MkDocs documentation: creating output directories, writing generated documentation files, and copying required assets.
    
    Args:
        mock_root: Mock object for the osa_project_root utility, which provides the project root path.
        mock_copy: Mock object for the shutil.copy function, used to copy asset files.
        mock_write_text: Mock object for the Path.write_text method, used to write documentation content to files.
        mock_mkdir: Mock object for the Path.mkdir method, used to create output directories.
        mock_config_manager: Mock object for the configuration manager dependency, injected into the DocGen instance.
    
    The test arranges a DocGen instance with mocked dependencies, then calls generate_documentation_mkdocs with sample file and module information. It asserts that the expected mocked methods (mkdir, write_text, and copy) are called, confirming the method performs the required filesystem operations.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    mock_root.return_value = Path("/fake/project")

    files_info = {
        "src/module1.py": {"structure": True},
        "src/module2.py": {"structure": False},
    }
    modules_info = {"src/module1": "Module 1 documentation"}

    # Act
    docgen.generate_documentation_mkdocs("src", files_info, modules_info)

    # Assert
    assert mock_mkdir.called
    assert mock_write_text.called
    mock_copy.assert_called_once()


def test_sanitize_name_basic(mock_config_manager):
    """
    Verifies the basic functionality of the name sanitization logic in DocGen.
    
    This test ensures that the `_sanitize_name` method correctly handles valid names,
    replaces dots with underscores, and prepends a 'v' to names that start with
    digits or special characters. This sanitization is necessary because certain
    characters (like dots or leading digits) can cause issues in file systems,
    URLs, or other contexts where the sanitized name might be used.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to
            initialize the DocGen object. This fixture provides a controlled
            environment for testing without external dependencies.
    
    Returns:
        This test does not return a value; it uses assertions to verify behavior.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    # Assert
    assert docgen._sanitize_name("valid_name") == "valid_name"
    assert docgen._sanitize_name("name.with.dots") == "name_with_dots"
    assert docgen._sanitize_name("1starts_with_digit") == "v1starts_with_digit"
    assert docgen._sanitize_name(".hidden") == "v.hidden".replace(".", "_")


def test_rename_invalid_dirs(mock_config_manager, tmp_path):
    """
    Verifies that the `_rename_invalid_dirs` method correctly renames directories that do not follow valid naming conventions.
        
    This test case ensures that directories starting with invalid characters (such as digits) are properly sanitized and renamed, while valid directory names remain unchanged within the specified temporary path. Specifically, it tests that a directory named "1invalid" is renamed to "v1invalid" (prepending a 'v' to make it valid), while a directory named "valid" remains unchanged.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
        tmp_path: A fixture providing a temporary directory path for creating test file structures.
    
    Why:
        This test validates the behavior of a method that sanitizes directory names to comply with naming conventions required by the OSA Tool's documentation pipeline. Directories starting with digits are invalid in certain contexts (e.g., as Python module names or for consistent documentation structuring), so the method renames them to ensure compatibility and avoid processing errors.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    invalid_dir = tmp_path / "1invalid"
    invalid_dir.mkdir()
    valid_dir = tmp_path / "valid"
    valid_dir.mkdir()

    # act
    docgen._rename_invalid_dirs(tmp_path)

    # Assert
    assert (tmp_path / "v1invalid").exists()
    assert (tmp_path / "valid").exists()


def test_add_init_files_creates_inits(mock_config_manager, tmp_path):
    """
    Verifies that the _add_init_files method correctly creates __init__.py files in directories containing Python modules.
    This ensures that Python packages are properly structured for import, which is a common requirement for documentation generation and repository organization.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object without external dependencies.
        tmp_path: A pytest fixture providing a temporary directory path for isolated file system operations during the test.
    
    The test performs the following steps:
    1. Creates a temporary directory structure with a Python module file.
    2. Calls the _add_init_files method on the root directory.
    3. Asserts that an __init__.py file is created in the subdirectory containing the module.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    subdir = tmp_path / "package"
    subdir.mkdir()
    py_file = subdir / "module.py"
    py_file.touch()

    # Act
    docgen._add_init_files(tmp_path)

    # Assert
    assert (subdir / "__init__.py").exists()


def test_purge_temp_files_removes_temp_dir(mock_config_manager, tmp_path):
    """
    Verifies that the purge_temp_files method successfully removes the temporary directory.
        
    This test case ensures that when a temporary directory named 'mkdocs_temp' exists within a given path, the _purge_temp_files method correctly identifies and deletes it along with its contents. The test creates the temporary directory and a file inside it, confirms the directory exists, calls the purge method, and then verifies the directory is removed.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
        tmp_path: A pytest fixture providing a temporary directory path for file system operations.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    temp_dir = tmp_path / "mkdocs_temp"
    temp_dir.mkdir()
    (temp_dir / "file.txt").touch()

    # Assert
    assert temp_dir.exists()
    docgen._purge_temp_files(tmp_path)
    assert not temp_dir.exists()


@pytest.mark.asyncio
async def test_generate_docstrings_for_functions_methods(mock_config_manager):
    """
    Verifies that the docstring generation process correctly handles both functions and methods simultaneously.
    
    This test ensures the internal `_generate_docstrings_for_items` method can process multiple item types (functions and methods) in a single operation, validating that the system correctly distinguishes and documents each type without mixing or omitting them.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object. This fixture provides controlled configuration for testing.
    
    Returns:
        None. This is a test method; its purpose is to assert behavior rather than return a value.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    async def mock_fetch_docstrings(parsed_structure, docstring_type, semaphore, rate_limit):
        return {
            file: {"functions": [("docstring", "func1")], "methods": [("docstring", "method1")], "classes": []}
            for file in parsed_structure
        }

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
async def test_generate_docstrings_for_classes(mock_config_manager):
    """
    Tests the generation of docstrings for classes by mocking the internal class-level docstring fetching logic.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object. This allows the test to run without real configuration dependencies.
    
    Returns:
        None. This is a test method, so it does not return a value but asserts expected behavior.
    
    Why:
        This test verifies that the docstring generation process correctly handles class-level documentation by mocking the underlying fetching function. It ensures that the system properly integrates class docstrings into the overall results structure for multiple files.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    async def mock_fetch_docstrings_for_class(filename, structure, semaphore, progress):
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
async def test_generate_docstrings_for_all_types(mock_config_manager):
    """
    Verifies that docstrings can be generated for all supported item types (functions, methods, and classes) simultaneously in a single operation.
    
    This test ensures the internal generation method correctly processes multiple file structures and returns organized results for each item type, confirming the system's ability to handle batch documentation generation.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object. This fixture provides controlled configuration for testing.
    
    Why:
        The method mocks the internal `_fetch_docstrings` call to simulate a successful docstring generation for all specified item types across multiple files, then validates that the results contain the expected keys for each type. This verifies the integration and data‑flow of the batch generation process without relying on external services.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)

    async def mock_fetch_docstrings(parsed_structure, docstring_type, semaphore, rate_limit):
        return {
            file: {
                "functions": [("docstring", "func1")],
                "methods": [("docstring", "method1")],
                "classes": [("docstring", "Class1")],
            }
            for file in parsed_structure
        }

    docgen._fetch_docstrings = mock_fetch_docstrings
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


def test_perform_code_augmentations(mock_config_manager):
    """
    Verifies that the `_perform_code_augmentations` method correctly inserts generated docstrings into the provided source code.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Why:
        This is a unit test that ensures the internal augmentation logic works as expected, specifically that docstrings are properly formatted and placed within the source code. It validates the integration between configuration, docstring generation, and code modification.
    
    Note:
        The test uses a fixed example of source code and expected docstring content to check the output. It asserts that the resulting dictionary contains the correct filename and that the inserted docstring matches the expected format.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
    args = (
        "file1.py",
        "def foo():\n\tdo_stuff()",
        {"functions": [("doc1", {"method_name": "foo"})], "methods": [], "classes": []},
    )

    # Act
    result = docgen._perform_code_augmentations(args)

    # Assert
    assert "file1.py" in result
    assert '\n\t"""\n\tdoc1\n\t"""\n\t' in result["file1.py"]


def test_run_in_executor_with_fake_augment(mock_config_manager):
    """
    Verifies that the DocGen class can correctly process file augmentation tasks using a concurrent executor.
    
    This test simulates the parallel execution of source code augmentation by mocking the project structure, source code, and generated docstrings. It uses a ThreadPoolExecutor to map a fake augmentation function over the provided file arguments and asserts that the results match the expected augmented strings. The test ensures that the DocGen class can handle concurrent processing of multiple files, which is critical for performance in real-world usage.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Note:
        The test does not call any actual DocGen methods; it only validates the underlying concurrent execution pattern with mocked data. This isolates the concurrency logic from other dependencies.
    """
    # Arrange
    docgen = DocGen(mock_config_manager)
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
async def test_get_project_source_code_with_config(tmp_path, mock_config_manager):
    """
    Tests the concurrent retrieval of project source code using a configuration manager.
    
    This test verifies that the `_get_project_source_code` method correctly reads and returns the content of multiple source files from a temporary directory, using a provided configuration manager and a semaphore to control concurrency. It ensures the method works as expected when integrated with the DocGen class.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path for creating test files.
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None.
    """
    # Arrange
    files = {"file1.py": "print('hello')", "file2.py": "print('world')"}

    for name, content in files.items():
        (tmp_path / name).write_text(content, encoding="utf-8")
    parsed_structure = {str(tmp_path / name): {"structure": True} for name in files}

    sem = asyncio.Semaphore(2)

    docgen = DocGen(config_manager=mock_config_manager)

    # Act
    result = await docgen._get_project_source_code(parsed_structure, sem)

    # Assert
    expected = {str(tmp_path / k): v for k, v in files.items()}
    assert result == expected


@pytest.mark.asyncio
async def test_write_augmented_code_with_config(tmp_path, mock_config_manager):
    """
    Verifies that the `_write_augmented_code` method correctly updates file contents on disk using the provided configuration and augmented code snippets.
    This test ensures that the method writes the new, augmented code to the correct files, overwriting the original content as intended.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path for file operations.
        mock_config_manager: A mocked configuration manager instance used to initialize the DocGen object.
    
    Returns:
        None
    """
    # Arrange
    files = ["file1.py", "file2.py"]
    for f in files:
        (tmp_path / f).write_text("old code", encoding="utf-8")
    parsed_structure = {str(tmp_path / f): {"structure": True} for f in files}
    augmented_code = [{str(tmp_path / files[0]): "new code 1"}, {str(tmp_path / files[1]): "new code 2"}]

    sem = asyncio.Semaphore(2)
    docgen = DocGen(config_manager=mock_config_manager)

    # Act
    await docgen._write_augmented_code(parsed_structure, augmented_code, sem)

    # Assert
    for i, f in enumerate(files):
        content = (tmp_path / f).read_text(encoding="utf-8")
        assert content == augmented_code[i][str(tmp_path / f)]
