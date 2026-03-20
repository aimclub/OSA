import pytest

from osa_tool.utils.response_cleaner import JsonProcessor, JsonParseError


def test_process_text_valid_json_object():
    """
    Tests the JsonProcessor.process_text method with a valid JSON object string.
    
    This test verifies that the method correctly processes a text containing a valid JSON object,
    returning the same JSON string without modification. Since the input is already well‑formed JSON,
    the method should not alter it, confirming that it handles valid inputs correctly.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    text = '{"name": "Alice", "age": 30}'

    # Act
    result = JsonProcessor.process_text(text)

    # Assert
    assert result == '{"name": "Alice", "age": 30}'


def test_process_text_valid_json_array():
    """
    Tests the JsonProcessor.process_text method with a valid JSON array input.
    
    This test verifies that the method correctly processes a string containing a well‑formed JSON array. It ensures that the extraction and cleaning logic does not alter valid JSON input, confirming that the method preserves the original content when no malformed patterns are present.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    text = '["apple", "banana"]'

    # Act
    result = JsonProcessor.process_text(text)

    # Assert
    assert result == '["apple", "banana"]'


def test_process_text_with_surrounding_text():
    """
    Tests the extraction of JSON content from text that includes surrounding non-JSON content.
    
    This test verifies that `JsonProcessor.process_text` correctly extracts a JSON
    object when it is embedded within a larger text block, such as within a code
    fence or surrounded by introductory and concluding text. The test ensures the
    method can isolate the valid JSON substring from extraneous text, which is
    essential for processing outputs from sources like LLMs or logs where JSON may
    be wrapped in explanatory or formatting text.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    text = 'Some intro\n```json\n{"key": "value"}\n```\nMore text'

    # Act
    result = JsonProcessor.process_text(text)

    # Assert
    assert result == '{"key": "value"}'


def test_process_text_removes_trailing_commas():
    """
    Tests that `JsonProcessor.process_text` removes trailing commas from JSON-like strings.
    
    This test verifies that the `process_text` method correctly handles strings
    containing trailing commas in both object and array structures, ensuring
    they are removed to produce valid JSON. The test is necessary because the
    `process_text` method is designed to clean malformed or embedded JSON text
    (e.g., from LLM outputs) where trailing commas are a common non‑JSON pattern.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    text = '{"a": 1, "b": 2,}'

    # Act
    result = JsonProcessor.process_text(text)

    # Assert
    assert result == '{"a": 1, "b": 2}'

    # Arrange
    text = '["x", "y",]'

    # Act
    result = JsonProcessor.process_text(text)

    # Assert
    assert result == '["x", "y"]'


def test_process_text_non_string_input():
    """
    Tests that `JsonProcessor.process_text` raises a `ValueError` when given non‑string input.
    
    This test ensures the method properly validates its input type, rejecting non‑string arguments (e.g., integers) with a clear error message. It is important because the method is designed to process text and cannot handle other data types.
    
    Args:
        None
    
    Returns:
        None
    """
    # Assert
    with pytest.raises(ValueError, match="Input must be a string."):
        JsonProcessor.process_text(123)


def test_parse_success_extract_key():
    """
    Tests that JsonProcessor.parse successfully extracts a value from JSON when given a specific key.
    
    This test verifies that the parse method correctly returns the string value associated with the 'overview' key from a JSON-formatted input string. It also validates that the method works with the optional `expected_key` and `expected_type` parameters, ensuring the extracted value matches the expected type and content.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    text = '{"overview": "System OK"}'

    # Act
    result = JsonProcessor.parse(text, expected_key="overview", expected_type=str)

    # Assert
    assert result == "System OK"


def test_parse_success_array_extraction():
    """
    Tests successful extraction of an array from JSON using JsonProcessor.parse.
    
    This method verifies that when a JSON string contains an array under a specified key, the parse method correctly extracts and returns that array. It is a test case and does not initialize any class fields.
    
    Args:
        None
    
    Returns:
        None
    
    Why:
    This test ensures that the JsonProcessor.parse function properly handles the extraction of a list value from a JSON object when both an expected_key and expected_type are provided, confirming the expected behavior for array data.
    """
    # Arrange
    text = '{"files": ["main.py", "utils.py"]}'

    # Act
    result = JsonProcessor.parse(text, expected_key="files", expected_type=list)

    # Assert
    assert result == ["main.py", "utils.py"]


def test_parse_type_mismatch_raises_error():
    """
    Tests that JsonProcessor.parse raises JsonParseError when the JSON value type does not match the provided expected_type.
    
    This test verifies that the parser correctly enforces type validation by raising an error when the parsed content (after any key extraction) is not of the specified type.
    
    Args:
        None
    
    Returns:
        None
    
    Note:
        This is a test method and does not initialize any class fields.
    """
    # Arrange
    text = '{"value": "string"}'

    # Assert
    with pytest.raises(JsonParseError):
        JsonProcessor.parse(text, expected_type=list)


def test_parse_invalid_json_raises_error():
    """
    Tests that parsing invalid JSON raises the expected error.
    
    This method verifies that the JsonProcessor.parse method raises a JsonParseError
    when provided with input text that is not valid JSON. It uses a simple non-JSON string
    to trigger the error, ensuring the parser correctly fails on malformed input.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    text = "Not JSON at all"

    # Assert
    with pytest.raises(JsonParseError):
        JsonProcessor.parse(text)


def test_parse_nested_valid_json():
    """
    Tests parsing of nested valid JSON from a text string.
    
    This test verifies that the JsonProcessor.parse method correctly extracts and
    parses a nested JSON structure embedded within surrounding text. The JSON
    includes an array containing a nested object with a boolean value and a null
    value.
    
    The test ensures the parser can handle a realistic example where JSON is surrounded by non-JSON text, validating correct extraction, type conversion (e.g., `true` to `True`, `null` to `None`), and deep equality of the resulting structure.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    text = 'Prefix {"data": [1, {"flag": true}], "null_val": null} Suffix'

    # Act
    result = JsonProcessor.parse(text)

    # Assert
    expected = {"data": [1, {"flag": True}], "null_val": None}
    assert result == expected
