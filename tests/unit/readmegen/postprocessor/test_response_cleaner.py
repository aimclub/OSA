from unittest.mock import patch

from osa_tool.readmegen.postprocessor.response_cleaner import JsonProcessor


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


def test_process_text_no_brackets_raises_value_error():
    # Assert
    try:
        JsonProcessor.process_text("Just plain text")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "No JSON start bracket" in str(e)


def test_process_text_mismatched_brackets():
    # Assert
    try:
        JsonProcessor.process_text("Text with { but no closing")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "No valid JSON end bracket" in str(e)


def test_process_text_non_string_input():
    # Assert
    try:
        JsonProcessor.process_text(123)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert str(e) == "Input must be a string."


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


def test_parse_fallback_to_list_when_expected_type_list():
    # Arrange
    text = "Not JSON at all"

    # Act
    result = JsonProcessor.parse(text, expected_type=list)

    # Assert
    assert result == ["Not JSON at all"]


def test_parse_fallback_wrap_in_list():
    # Arrange
    text = "Error occurred"

    # Act
    result = JsonProcessor.parse(text, wrap_in_list=True)

    # Assert
    assert result == ["Error occurred"]


def test_parse_fallback_to_dict():
    # Arrange
    text = "Raw response"

    # Act
    result = JsonProcessor.parse(text, expected_type=dict)

    # Assert
    assert result == {"raw": "Raw response"}


def test_parse_fallback_dict_with_custom_key():
    # Arrange
    text = "Fallback content"

    # Act
    result = JsonProcessor.parse(text, expected_key="summary", expected_type=dict)

    # Assert
    assert result == {"summary": "Fallback content"}


def test_parse_type_mismatch_triggers_fallback():
    # Arrange
    text = '{"value": "string"}'

    # Act
    result = JsonProcessor.parse(text, expected_type=list)
    # Assert
    assert result == [text.strip()]


def test_parse_nested_valid_json():
    # Arrange
    text = 'Prefix {"data": [1, {"flag": true}], "null_val": null} Suffix'

    # Act
    result = JsonProcessor.parse(text)

    # Assert
    expected = {"data": [1, {"flag": True}], "null_val": None}
    assert result == expected


def test_parse_logs_warning_on_failure():
    with patch("osa_tool.readmegen.postprocessor.response_cleaner.logger") as mock_logger:
        # Act
        JsonProcessor.parse("invalid", expected_type=dict)

        # Assert
        mock_logger.warning.assert_called_once()
        assert "Failed to parse JSON" in mock_logger.warning.call_args[0][0]
