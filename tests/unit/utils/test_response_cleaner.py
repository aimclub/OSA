import pytest

from osa_tool.utils.response_cleaner import JsonParseError, JsonProcessor


def test_unknown_type_preserves_earliest_object_root():
    assert JsonProcessor.parse('answer: {"result": [1, 2]}') == {"result": [1, 2]}


def test_keyed_list_type_applies_after_object_lookup():
    assert JsonProcessor.parse('{"files": ["main.py"]}', expected_key="files", expected_type=list) == ["main.py"]


def test_non_json_fence_does_not_hide_later_json():
    response = '```python\nprint("example")\n```\n[{"answer": true}]'
    assert JsonProcessor.parse(response, expected_type=list) == [{"answer": True}]


def test_parse_repairs_unterminated_string_before_failing():
    assert JsonProcessor.parse('{"name":"value}', expected_type=dict) == {"name": "value"}


def test_parse_repairs_unquoted_string_values():
    assert JsonProcessor.parse('{"name":value}', expected_type=dict) == {"name": "value"}


def test_parse_repairs_json_before_expected_key_and_type_validation():
    assert JsonProcessor.parse('{"files":["main.py",}', expected_key="files", expected_type=list) == ["main.py"]


def test_parse_raises_json_parse_error_when_json_repair_fails(monkeypatch):
    def fail_repair(*args, **kwargs):
        raise ValueError("cannot repair")

    monkeypatch.setattr("osa_tool.utils.response_cleaner.repair_json", fail_repair)

    with pytest.raises(JsonParseError, match="cannot repair"):
        JsonProcessor.parse("not json", expected_type=dict)
