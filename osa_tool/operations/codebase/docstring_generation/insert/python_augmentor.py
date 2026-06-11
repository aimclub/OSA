import libcst as cst
from libcst.metadata import PositionProvider

from osa_tool.operations.codebase.docstring_generation.insert.base_augmentor import BaseAugmentor
from osa_tool.operations.codebase.docstring_generation.docstring_transformer import DocstringTransformer


class PythonAugmentor(BaseAugmentor):

    def augment(self, file: str, source_code: str, docstrings: dict) -> dict[str, str]:
        if not docstrings:
            return {file: source_code}

        module = cst.parse_module(source_code)
        wrapper = cst.MetadataWrapper(module)

        transformer = DocstringTransformer(docstrings, source_code.splitlines(True), module.default_indent)

        new_module = wrapper.visit(transformer)

        return {file: new_module.code}
