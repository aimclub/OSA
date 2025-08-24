import pytest

from osa_tool.readmegen.postprocessor.response_cleaner import process_text


def test_valid_json_object_simple():
    # Arrange
    text = 'Some text before {"a": 1, "b": 2} some text after'

    # Act
    result = process_text(text)

    # Assert
    assert result == '{"a": 1, "b": 2}'


def test_valid_json_array_simple():
    # Arrange
    text = "prefix [1, 2, 3] suffix"

    # Act
    result = process_text(text)

    # Assert
    assert result == "[1, 2, 3]"


def test_python_literals_are_converted():
    # Arrange
    text = "{'key': None, 'flag': True, 'other': False}"

    # Act
    result = process_text(text)

    # Assert
    assert "null" in result
    assert "true" in result
    assert "false" in result


def test_trailing_comma_removed_object():
    # Arrange
    text = "{'a': 1, 'b': 2,}"

    # Act
    result = process_text(text)

    # Assert
    assert result == "{'a': 1, 'b': 2}"


def test_trailing_comma_removed_array():
    # Arrange
    text = "[1, 2, 3,]"

    # Act
    result = process_text(text)

    # Assert
    assert result == "[1, 2, 3]"


def test_prefers_first_opening_bracket():
    # Arrange
    text = 'garbage [99] prefix {"x": 42}'

    # Act
    result = process_text(text)

    # Assert
    assert result == "[99]"


def test_returns_longest_valid_block():
    # Arrange
    text = "{ 'outer': { 'inner': 123 } } and noise"

    # Act
    result = process_text(text)

    # Assert
    assert result.startswith("{")
    assert result.endswith("}")


def test_raises_if_no_json_start():
    # Assert
    with pytest.raises(ValueError, match="No JSON start bracket found"):
        process_text("just plain text without brackets")


def test_raises_if_no_matching_end():
    # Assert
    with pytest.raises(ValueError, match="No valid JSON end bracket found"):
        process_text("something { 'broken': 1 ")


def test_multiple_blocks_takes_first():
    # Arrange
    text = 'noise [1,2] more {"a": 1}'

    # Act
    result = process_text(text)

    # Assert
    assert result == "[1,2]"


def test_nested_array_inside_object():
    # Arrange
    text = "{'numbers': [1,2,3,]}"

    # Act
    result = process_text(text)

    # Assert
    assert "'numbers'" in result
    assert "[1,2,3]" in result
