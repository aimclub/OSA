import pytest

from osa_tool.readmegen.postprocessor.response_cleaner import process_text


@pytest.mark.parametrize(
    "input_text, expected_output",
    [
        ('```json\n{"a": 1, "b": 2}```', '{"a": 1, "b": 2}'),
        ('json   {"foo": "bar"}   ', '{"foo": "bar"}'),
        ('```json plaintext {"nested": "test"}```', '{"nested": "test"}'),
        ('Some text before\n{"valid": "json"}\nSome text after', '{"valid": "json"}'),
        ('\n\nplaintext\n\n{"multi": "line"}\n\n', '{"multi": "line"}'),
        ('{"clean": "data"}', '{"clean": "data"}'),
    ],
)
def test_process_text_json_cases(input_text, expected_output):
    """
    Test that `process_text` correctly extracts JSON from various input formats.
    
    Parameters
    ----------
    input_text
        The raw text containing JSON, possibly wrapped in code fences or surrounded by other text.
    expected_output
        The expected JSON string that should be returned by `process_text`.
    
    Returns
    -------
    None
        This function does not return a value; it raises an AssertionError if the
        processed output does not match the expected output.
    """
    assert process_text(input_text) == expected_output
