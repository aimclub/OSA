"""Tests for the adapter-based OSA_TreeSitter parser (core/osa_parser.py).

This is the parser actually used by the docstring-generation pipeline; the tests cover
file discovery, per-language structure extraction and the function index.
"""

from osa_tool.operations.codebase.docstring_generation.core.osa_parser import OSA_TreeSitter
from osa_tool.operations.codebase.docstring_generation.adapters.python_adapter import PythonAdapter
from osa_tool.operations.codebase.docstring_generation.adapters.javascript_adapter import JavaScriptAdapter
from osa_tool.operations.codebase.docstring_generation.adapters.typescript_adapter import TypeScriptAdapter, TSXAdapter

PY_HELPER = "def helper(x):\n    return x + 1\n"
PY_MAIN = (
    "from helper import helper\n\n\n"
    "def compute(x):\n"
    "    return helper(x)\n\n\n"
    "class Runner:\n"
    "    def run(self):\n"
    "        return self.transform()\n\n"
    "    def transform(self):\n"
    "        return compute(1)\n"
)


def _write(tmp_path, name, content):
    p = tmp_path / name
    # newline="\n" avoids the platform newline translation (\n -> \r\n on Windows) so
    # file content matches exactly what we write
    p.write_text(content, encoding="utf-8", newline="\n")
    return str(p)


# --- files_list -------------------------------------------------------------


def test_files_list_directory_collects_source_files(tmp_path):
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, "b.js", "const x = 1;\n")
    _write(tmp_path, "c.ts", "const y: number = 1;\n")
    _write(tmp_path, "readme.md", "# not source\n")

    files, status = OSA_TreeSitter(str(tmp_path)).files_list(str(tmp_path))

    names = sorted(f.rsplit("\\", 1)[-1].rsplit("/", 1)[-1] for f in files)
    assert names == ["a.py", "b.js", "c.ts"]
    assert status == 0


def test_files_list_ignores_non_source_extensions(tmp_path):
    _write(tmp_path, "notes.txt", "hello\n")
    _write(tmp_path, "data.json", "{}\n")

    files, _ = OSA_TreeSitter(str(tmp_path)).files_list(str(tmp_path))

    assert files == []


def test_files_list_default_ignores_init(tmp_path):
    _write(tmp_path, "mod.py", "x = 1\n")
    _write(tmp_path, "__init__.py", "\n")

    files, _ = OSA_TreeSitter(str(tmp_path)).files_list(str(tmp_path))

    names = [f.replace("\\", "/").rsplit("/", 1)[-1] for f in files]
    assert "mod.py" in names
    assert "__init__.py" not in names


def test_files_list_applies_ignore_list(tmp_path):
    """ignore_list skips both files under an ignored directory and files whose basename
    is listed (parity with the legacy parser)."""
    (tmp_path / "ignore1").mkdir()
    (tmp_path / "allow1").mkdir()
    (tmp_path / "allow1" / "ignore2").mkdir()
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, "ignore1/b.py", "x = 1\n")
    _write(tmp_path, "allow1/__init__.py", "x = 1\n")
    _write(tmp_path, "allow1/b_allow.py", "x = 1\n")
    _write(tmp_path, "allow1/ignore2/c.py", "x = 1\n")

    ignore_list = ["ignore1", "allow1/ignore2", "__init__.py"]
    files, _ = OSA_TreeSitter(str(tmp_path), ignore_list).files_list(str(tmp_path))

    names = sorted(f.replace("\\", "/").rsplit("/", 1)[-1] for f in files)
    assert names == ["a.py", "b_allow.py"]


def test_files_list_target_files_only(tmp_path):
    _write(tmp_path, "a.py", "x = 1\n")
    _write(tmp_path, "b.py", "y = 2\n")

    ts = OSA_TreeSitter(str(tmp_path), target_files=["a.py"])
    files, _ = ts.files_list(str(tmp_path))

    assert len(files) == 1
    assert files[0].endswith("a.py")


# --- _get_adapter -----------------------------------------------------------


def test_get_adapter_maps_extension_to_adapter(tmp_path):
    ts = OSA_TreeSitter(str(tmp_path))
    assert isinstance(ts._get_adapter("x.py"), PythonAdapter)
    assert isinstance(ts._get_adapter("x.js"), JavaScriptAdapter)
    assert isinstance(ts._get_adapter("x.ts"), TypeScriptAdapter)
    assert isinstance(ts._get_adapter("x.tsx"), TSXAdapter)
    assert ts._get_adapter("x.unknown") is None


# --- open_file --------------------------------------------------------------


def test_open_file_reads_content(tmp_path):
    path = _write(tmp_path, "a.py", "print('hi')\n")
    assert OSA_TreeSitter(str(tmp_path)).open_file(path) == "print('hi')\n"


# --- extract_structure: Python ----------------------------------------------


def test_extract_structure_python_class_and_function(tmp_path):
    _write(tmp_path, "helper.py", PY_HELPER)
    main = _write(tmp_path, "main.py", PY_MAIN)

    res = OSA_TreeSitter(str(tmp_path)).extract_structure(main)

    kinds = [item["type"] for item in res["structure"]]
    assert "function" in kinds
    assert "class" in kinds

    func = next(i for i in res["structure"] if i["type"] == "function")
    assert func["details"]["method_name"] == "compute"

    cls = next(i for i in res["structure"] if i["type"] == "class")
    assert cls["name"] == "Runner"
    method_names = [m["method_name"] for m in cls["methods"]]
    assert "run" in method_names and "transform" in method_names


def test_extract_structure_python_imports_and_calls(tmp_path):
    _write(tmp_path, "helper.py", PY_HELPER)
    main = _write(tmp_path, "main.py", PY_MAIN)

    res = OSA_TreeSitter(str(tmp_path)).extract_structure(main)

    # import of `helper` resolved to helper.py under cwd
    assert "helper" in res["imports"]

    func = next(i for i in res["structure"] if i["type"] == "function")
    assert "helper" in func["details"]["method_calls"]


def test_extract_structure_unknown_extension_is_empty(tmp_path):
    path = _write(tmp_path, "notes.txt", "not code\n")
    res = OSA_TreeSitter(str(tmp_path)).extract_structure(path)
    assert res == {"structure": [], "imports": {}}


# --- extract_structure: JS / TS smoke ---------------------------------------


def test_extract_structure_javascript_function(tmp_path):
    path = _write(tmp_path, "u.js", "function greet(name) {\n  return name;\n}\n")
    res = OSA_TreeSitter(str(tmp_path)).extract_structure(path)
    names = [i["details"]["method_name"] for i in res["structure"] if i["type"] == "function"]
    assert "greet" in names


def test_extract_structure_typescript_class(tmp_path):
    path = _write(tmp_path, "q.ts", "class Queue {\n  push(v: number) {\n    return v;\n  }\n}\n")
    res = OSA_TreeSitter(str(tmp_path)).extract_structure(path)
    cls = next(i for i in res["structure"] if i["type"] == "class")
    assert cls["name"] == "Queue"
    assert "push" in [m["method_name"] for m in cls["methods"]]


# --- analyze_directory ------------------------------------------------------


def test_analyze_directory_returns_structure_per_file(tmp_path):
    _write(tmp_path, "helper.py", PY_HELPER)
    _write(tmp_path, "main.py", PY_MAIN)

    results = OSA_TreeSitter(str(tmp_path)).analyze_directory(str(tmp_path))

    assert len(results) == 2
    assert all("structure" in data and "imports" in data for data in results.values())


# --- build_function_index ---------------------------------------------------


def test_build_function_index_indexes_methods_and_functions(tmp_path):
    _write(tmp_path, "helper.py", PY_HELPER)
    _write(tmp_path, "main.py", PY_MAIN)

    ts = OSA_TreeSitter(str(tmp_path))
    results = ts.analyze_directory(str(tmp_path))
    index = OSA_TreeSitter.build_function_index(results)

    # top-level function by name
    assert "compute" in index
    assert "helper" in index
    # method by both short and qualified name
    assert "run" in index
    assert "Runner.run" in index
    # each entry carries its source file
    assert index["Runner.run"]["file"].endswith("main.py")
    # method entries keep their owning class name (context extractor relies on it)
    assert index["Runner.run"]["class"] == "Runner"
    assert index["run"]["class"] == "Runner"


def test_build_function_index_empty_input():
    assert OSA_TreeSitter.build_function_index({}) == {}
