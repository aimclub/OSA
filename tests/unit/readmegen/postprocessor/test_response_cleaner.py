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
    assert process_text(input_text) == expected_output
