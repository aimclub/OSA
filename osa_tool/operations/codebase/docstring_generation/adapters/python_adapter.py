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
        return {}

    def resolve_method_calls(self, node, sv):
        return []