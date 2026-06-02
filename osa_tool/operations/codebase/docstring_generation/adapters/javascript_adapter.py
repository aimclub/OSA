import tree_sitter_javascript as tsjs
from tree_sitter import Parser, Language
from osa_tool.operations.codebase.docstring_generation.adapters.typescript_adapter import TypeScriptAdapter


class JavaScriptAdapter(TypeScriptAdapter):
    EXTENSIONS = (".js", ".jsx")

    def build_parser(self):
        return Parser(Language(tsjs.language()))
