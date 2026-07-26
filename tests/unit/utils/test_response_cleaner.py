from osa_tool.utils.response_cleaner import JsonProcessor


def test_unknown_type_preserves_earliest_object_root():
    assert JsonProcessor.parse('answer: {"result": [1, 2]}') == {"result": [1, 2]}


def test_keyed_list_type_applies_after_object_lookup():
    assert JsonProcessor.parse('{"files": ["main.py"]}', expected_key="files", expected_type=list) == ["main.py"]


def test_non_json_fence_does_not_hide_later_json():
    response = '```python\nprint("example")\n```\n[{"answer": true}]'
    assert JsonProcessor.parse(response, expected_type=list) == [{"answer": True}]
