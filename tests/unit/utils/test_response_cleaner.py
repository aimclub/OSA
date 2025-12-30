import pytest

from osa_tool.utils.response_cleaner import JsonProcessor, JsonParseError


def test_process_text_valid_json_object():
    # Arrange
    text = '{"name": "Alice", "age": 30}'

    # Act
    result = JsonProcessor.process_text(text)

    # Assert
    assert result == '{"name": "Alice", "age": 30}'


def test_process_text_valid_json_array():
    # Arrange
    text = '["apple", "banana"]'

    # Act
    result = JsonProcessor.process_text(text)

    # Assert
    assert result == '["apple", "banana"]'


def test_process_text_with_surrounding_text():
    # Arrange
    text = 'Some intro\n```json\n{"key": "value"}\n```\nMore text'

    # Act
    result = JsonProcessor.process_text(text)

    # Assert
    assert result == '{"key": "value"}'


def test_process_text_removes_trailing_commas():
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
    # Assert
    with pytest.raises(ValueError, match="Input must be a string."):
        JsonProcessor.process_text(123)


def test_parse_success_extract_key():
    # Arrange
    text = '{"overview": "System OK"}'

    # Act
    result = JsonProcessor.parse(text, expected_key="overview", expected_type=str)

    # Assert
    assert result == "System OK"


def test_parse_success_array_extraction():
    # Arrange
    text = '{"files": ["main.py", "utils.py"]}'

    # Act
    result = JsonProcessor.parse(text, expected_key="files", expected_type=list)

    # Assert
    assert result == ["main.py", "utils.py"]


def test_parse_type_mismatch_raises_error():
    # Arrange
    text = '{"value": "string"}'

    # Assert
    with pytest.raises(JsonParseError):
        JsonProcessor.parse(text, expected_type=list)


def test_parse_invalid_json_raises_error():
    # Arrange
    text = "Not JSON at all"

    # Assert
    with pytest.raises(JsonParseError):
        JsonProcessor.parse(text)


def test_parse_nested_valid_json():
    # Arrange
    text = 'Prefix {"data": [1, {"flag": true}], "null_val": null} Suffix'

    # Act
    result = JsonProcessor.parse(text)

    # Assert
    expected = {"data": [1, {"flag": True}], "null_val": None}
    assert result == expected
