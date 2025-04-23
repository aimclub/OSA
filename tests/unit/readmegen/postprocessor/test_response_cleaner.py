import pytest

from osa_tool.readmegen.postprocessor.response_cleaner import clean_llm_response, process_text, remove_json_prefix, \
    remove_plaintext_prefix


@pytest.mark.parametrize("input_text, expected_output", [
    ('"""Some text"""', "Some text"),
    ("'''Some text'''", "Some text"),
    ('"Some text"', "Some text"),
    ("'Some text'", "Some text"),
    ("`Some text`", "Some text"),
    ('', ''),
    ('Some text', 'Some text'),
])
def test_clean_llm_response(input_text, expected_output):
    assert clean_llm_response(input_text) == expected_output


@pytest.mark.parametrize("input_text, expected_output", [
    ("plaintext This is a response", "This is a response"),
    ("plaintext", ""),
    ("no-prefix", "no-prefix"),
])
def test_remove_plaintext_prefix(input_text, expected_output):
    assert remove_plaintext_prefix(input_text) == expected_output


@pytest.mark.parametrize("input_text, expected_output", [
    ('json {"key": "value"}', '{"key": "value"}'),
    ("json", ""),
    ("no-prefix", "no-prefix"),
])
def test_remove_json_prefix(input_text, expected_output):
    assert remove_json_prefix(input_text) == expected_output


@pytest.mark.parametrize("input_text, expected_output", [
    ('"""plaintext This is a simple response"""', "This is a simple response"),
    ('"""json {"key": "value"}"""', '{"key": "value"}'),
    ('"""json plaintext This is mixed prefix"""', "This is mixed prefix"),
    ('"""Some normal text"""', "Some normal text"),
    ('json {"key": "value"}', '{"key": "value"}'),
])
def test_process_text(input_text, expected_output):
    assert process_text(input_text) == expected_output
