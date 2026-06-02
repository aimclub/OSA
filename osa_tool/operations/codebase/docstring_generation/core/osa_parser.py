import os
from pathlib import Path

from osa_tool.operations.codebase.docstring_generation.core.source_view import SourceView

from osa_tool.operations.codebase.docstring_generation.adapters.python_adapter import PythonAdapter
from osa_tool.operations.codebase.docstring_generation.adapters.javascript_adapter import JavaScriptAdapter
from osa_tool.operations.codebase.docstring_generation.adapters.typescript_adapter import TypeScriptAdapter


class OSA_TreeSitter:

    ADAPTERS = [
        PythonAdapter(),
        JavaScriptAdapter(),
        TypeScriptAdapter(),
    ]

    def __init__(self, scripts_path: str, ignore_list: list[str] = None, target_files: list[str] = None):

        self.cwd = scripts_path
        self.ignore_list = ignore_list or ["__init__.py"]
        self.target_files = target_files

    def files_list(self, path: str):
        exts = tuple(ext for a in self.ADAPTERS for ext in a.EXTENSIONS)

        script_files = []
        if self.target_files:
            for f in self.target_files:
                p = Path(os.path.join(self.cwd, f)).resolve()

                if p.exists() and p.suffix in exts:
                    script_files.append(str(p))

            return script_files, 0

        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for f in files:
                    if f.endswith(exts):
                        script_files.append(os.path.join(root, f))

            return script_files, 0

        return [], 0

    def _get_adapter(self, filename):
        for adapter in self.ADAPTERS:
            if filename.endswith(adapter.EXTENSIONS):
                return adapter

        return None

    def extract_structure(self, filename: str):
        adapter = self._get_adapter(filename)
        if not adapter:
            return {
                "structure": [],
                "imports": {},
            }

        parser = adapter.build_parser()
        source = self.open_file(filename)
        sv = SourceView(source)
        tree = parser.parse(source.encode())
        root = tree.root_node

        imports = adapter.extract_imports(root, sv, self.cwd)

        result = {
            "structure": [],
            "imports": imports,
        }

        def walk(node, class_ctx=None):
            if adapter.is_class(node):
                class_name = adapter.get_name(node, sv)
                cls = {
                    "type": "class",
                    "name": class_name,
                    "docstring": adapter.get_docstring(node, sv),
                    "start_line": node.start_point[0] + 1,
                    "methods": [],
                    "attributes": adapter.get_attributes(node, sv),
                    "decorators": adapter.get_decorators(node, sv),
                }

                for c in node.children:
                    walk(c, cls)

                result["structure"].append(cls)

                return

            if adapter.is_function(node):
                fn = {
                    "class_name": (class_ctx["name"] if class_ctx else None),
                    "method_name": adapter.get_name(node, sv),
                    "arguments": adapter.get_parameters(node, sv),
                    "docstring": adapter.get_docstring(node, sv),
                    "start_line": node.start_point[0] + 1,
                    "source_code": sv.text(node),
                    "method_calls": adapter.resolve_method_calls(node, sv),
                    "decorators": adapter.get_decorators(node, sv),
                }

                if class_ctx:
                    class_ctx["methods"].append(fn)

                else:
                    result["structure"].append({"type": "function", "details": fn})

            for c in node.children:
                walk(c, class_ctx)

        walk(root)

        return result

    @staticmethod
    def open_file(file: str):
        with open(file, "rb") as f:
            return f.read().decode("utf-8", errors="ignore")

    def analyze_directory(self, path: str):
        results = {}
        files, _ = self.files_list(path)

        for f in files:
            results[f] = self.extract_structure(f)

        return results

    @staticmethod
    def build_function_index(results: dict):
        index = {}
        for file, data in results.items():
            for item in data["structure"]:
                if item["type"] == "class":
                    for m in item["methods"]:
                        full = f"{item['name']}." f"{m['method_name']}"

                        index[full] = {
                            **m,
                            "file": file,
                        }

                        index[m["method_name"]] = {
                            **m,
                            "file": file,
                        }
                else:
                    d = item["details"]
                    index[d["method_name"]] = {
                        **d,
                        "file": file,
                    }

        return index
