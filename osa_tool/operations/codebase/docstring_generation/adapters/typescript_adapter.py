import tree_sitter_typescript as tstypescript

from tree_sitter import Parser, Language

from osa_tool.operations.codebase.docstring_generation.adapters.base import LanguageAdapter


class TypeScriptAdapter(LanguageAdapter):

    EXTENSIONS = (".ts", ".tsx")

    def build_parser(self):
        return Parser(Language(tstypescript.language_typescript()))

    def is_class(self, node):
        return node.type == "class_declaration"

    def is_function(self, node):

        return node.type in (
            "function_declaration",
            "method_definition",
            "arrow_function",
        )

    def get_name(self, node, sv):
        n = node.child_by_field_name("name")

        return sv.text(n) if n else "anonymous"

    def _get_doc_owner(self, node):
        parent = node.parent

        if not parent:
            return node

        # export function/class
        if parent.type == "export_statement":
            return parent

        # decorators wrapper
        if parent.type == "decorator":
            return parent

        return node

    def get_docstring(self, node, sv):

        owner = self._get_doc_owner(node)
        current = owner.prev_sibling
        while current:
            text = sv.text(current).strip()

            # skip whitespace-like nodes
            if not text:
                current = current.prev_sibling
                continue

            # jsdoc comment
            if current.type == "comment":

                if text.startswith("/**"):
                    return text

                return None

            # decorators
            if current.type == "decorator":
                current = current.prev_sibling
                continue

            break

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
            if c.type in (
                "public_field_definition",
                "field_definition",
                "property_signature",
            ):
                name = c.child_by_field_name("name")
                if name:
                    attrs.append(sv.text(name))

        return attrs

    def get_parameters(self, node, sv):
        params = []
        pnode = node.child_by_field_name("parameters")

        if not pnode:
            return params

        for c in pnode.children:
            if c.type in (
                "identifier",
                "required_parameter",
                "optional_parameter",
            ):
                params.append(sv.text(c))

        return params

    def extract_imports(self, root, sv, cwd):
        return {}

    def resolve_method_calls(self, node, sv):
        return []