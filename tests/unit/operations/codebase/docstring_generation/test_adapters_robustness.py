from osa_tool.operations.codebase.docstring_generation.adapters.python_adapter import PythonAdapter
from osa_tool.operations.codebase.docstring_generation.core.osa_parser import OSA_TreeSitter

# --- #5: class-field arrow name resolution (TypeScript adapter) --------------


def _method_names(res):
    names = []
    for item in res["structure"]:
        if item.get("type") == "class":
            names += [m["method_name"] for m in item["methods"]]
        elif item.get("type") == "function":
            names.append(item["details"]["method_name"])
    return names


def test_class_field_arrow_gets_name(tmp_path):
    f = tmp_path / "c.ts"
    f.write_text(
        "class C {\n  greet = (name: string): string => 'hi ' + name;\n}\n",
        encoding="utf-8",
    )
    res = OSA_TreeSitter(str(tmp_path)).extract_structure(str(f))
    names = _method_names(res)
    assert "greet" in names
    assert "anonymous" not in names


def test_regular_arrow_const_still_named(tmp_path):
    f = tmp_path / "u.ts"
    f.write_text("export const mul = (a, b) => a * b;\n", encoding="utf-8")
    res = OSA_TreeSitter(str(tmp_path)).extract_structure(str(f))
    assert "mul" in _method_names(res)
    assert "anonymous" not in _method_names(res)


# --- #6: parenthesized / multi-line Python from-imports ----------------------


def test_grouped_import_clean_keys(tmp_path):
    (tmp_path / "mod.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    mapping = PythonAdapter._resolve_import_path("from mod import (a, b)", str(tmp_path))
    assert set(mapping.keys()) == {"a", "b"}
    assert not any("(" in k or ")" in k for k in mapping)


def test_multiline_grouped_import_clean_keys(tmp_path):
    (tmp_path / "mod.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    text = "from mod import (\n    a,\n    b,\n    c,\n)"
    mapping = PythonAdapter._resolve_import_path(text, str(tmp_path))
    assert set(mapping.keys()) == {"a", "b", "c"}


def test_grouped_import_with_alias(tmp_path):
    (tmp_path / "mod.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    mapping = PythonAdapter._resolve_import_path("from mod import (a as x, b)", str(tmp_path))
    assert set(mapping.keys()) == {"x", "b"}
    assert mapping["x"]["class"] == "a"


def test_plain_import_still_works(tmp_path):
    (tmp_path / "mod.py").write_text("a = 1\n", encoding="utf-8")
    mapping = PythonAdapter._resolve_import_path("from mod import a", str(tmp_path))
    assert set(mapping.keys()) == {"a"}
