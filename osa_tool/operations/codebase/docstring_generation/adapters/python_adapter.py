import os

import tree_sitter_python as tspython
from tree_sitter import Parser, Language
from osa_tool.operations.codebase.docstring_generation.adapters.base import LanguageAdapter


class PythonAdapter(LanguageAdapter):

    EXTENSIONS = (".py",)

    def build_parser(self):
        return Parser(Language(tspython.language()))

    def is_class(self, node):
        return node.type == "class_definition"

    def is_function(self, node):
        return node.type == "function_definition"

    def get_name(self, node, sv):

        n = node.child_by_field_name("name")

        return sv.text(n) if n else "anonymous"

    def get_docstring(self, node, sv):

        for c in node.children:
            if c.type == "block":
                for cc in c.children:
                    if cc.type == "expression_statement":
                        for s in cc.children:
                            if s.type == "string":
                                return sv.text(s)

        return None

    def get_decorators(self, node, sv):
        decs = []
        for c in node.children:

            if c.type == "decorator":
                decs.append(sv.text(c))

        return decs

    def get_attributes(self, node, sv):
        attrs = []
        for c in node.children:
            if c.type == "expression_statement":
                for cc in c.children:
                    if cc.type == "assignment":
                        left = cc.child_by_field_name("left")
                        if left:
                            attrs.append(sv.text(left))

        return attrs

    def get_parameters(self, node, sv):
        params = []
        pnode = node.child_by_field_name("parameters")
        if not pnode:
            return params

        for c in pnode.children:
            if c.type == "identifier":
                params.append(sv.text(c))

        return params

    def extract_imports(self, root, sv, cwd):
        import_map = {}
        for node in root.children:
            if node.type in ("import_statement", "import_from_statement"):
                import_map.update(self._resolve_import_path(sv.text(node), cwd))

        return import_map

    @staticmethod
    def _resolve_import_path(import_text, cwd):
        import_mapping = {}
        text = import_text.strip()

        if text.startswith("from"):
            try:
                from_part, import_part = text.split("import", 1)
            except ValueError:
                return import_mapping

            module_name = from_part.replace("from", "").strip()
            module_path = os.path.join(cwd, *module_name.split(".")) + ".py"
            if not os.path.exists(module_path):
                return import_mapping

            # a grouped import `from x import (a, b)` (possibly multi-line) keeps the
            # parentheses/newlines in the raw text; strip them so the names stay clean
            import_part = import_part.strip().strip("()").replace("\\", " ")

            for entity in (e.strip().strip("()") for e in import_part.split(",")):
                if not entity or entity == "*":
                    continue
                if " as " in entity:
                    imported_name, alias_name = (e.strip() for e in entity.split(" as ", 1))
                else:
                    imported_name = alias_name = entity
                import_mapping[alias_name] = {
                    "module": module_name,
                    "class": imported_name,
                    "path": module_path,
                }

        elif text.startswith("import"):
            parts = text.replace("import", "").strip().split()
            if not parts:
                return import_mapping
            if "as" in parts:
                module_name = parts[0]
                alias_name = parts[parts.index("as") + 1]
            else:
                module_name = alias_name = parts[0]

            module_path = os.path.join(cwd, *module_name.split(".")) + ".py"
            if os.path.exists(module_path):
                import_mapping[alias_name] = {"module": module_name, "path": module_path}

        return import_mapping

    def resolve_method_calls(self, node, sv):
        block = next((c for c in node.children if c.type == "block"), None)
        if not block:
            return []

        calls = set()

        def walk(n):
            if n.type == "function_definition" and n is not node:
                return
            if n.type == "call":
                target = n.child_by_field_name("function")
                if target:
                    text = sv.text(target).strip()
                    if text:
                        calls.add(text)
            for c in n.children:
                walk(c)

        walk(block)

        return sorted(calls)
