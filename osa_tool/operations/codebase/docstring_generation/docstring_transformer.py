import libcst as cst
from libcst import (
    CSTTransformer,
    SimpleStatementLine,
    Expr,
    SimpleString,
    IndentedBlock,
)
from typing import Sequence


class DocstringTransformer(CSTTransformer):
    """
    Transformer to insert/update docstrings,
    by built qualified targets.
    """

    def __init__(self, generated_docstrings: dict):
        self.generated_docstrings = generated_docstrings
        self.targets: dict[str, str] = self._build_targets()
        self.class_stack: list[str] = []

    def _build_targets(self) -> dict[str, str]:
        targets: dict[str, str] = {}

        for _type, generated in self.generated_docstrings.items():
            match _type:
                case "methods":
                    for docstring, m in generated:
                        class_name = m["class_name"]
                        method_name = m["method_name"]
                        targets[f"{class_name}.{method_name}"] = docstring

                case "functions":
                    for docstring, f in generated:
                        targets[f["function_name"]] = docstring

                case "classes":
                    for docstring, c in generated:
                        targets[c] = docstring

        return targets

    def _make_doc(self, text: str) -> SimpleStatementLine:
        return SimpleStatementLine(body=[Expr(value=SimpleString(f'"""{text}"""'))])

    def _has_docstring(self, body: Sequence[cst.BaseStatement]) -> bool:
        return (
            body
            and isinstance(body[0], SimpleStatementLine)
            and len(body[0].body) == 1
            and isinstance(body[0].body[0], Expr)
            and isinstance(body[0].body[0].value, SimpleString)
        )

    def _process_block(self, block: IndentedBlock, key: str) -> IndentedBlock:
        body = list(block.body)
        new_doc = self._make_doc(self.targets[key])

        if self._has_docstring(body):
            body[0] = new_doc
        else:
            body.insert(0, new_doc)

        return block.with_changes(body=tuple(body))

    def visit_ClassDef(self, node: cst.ClassDef):
        self.class_stack.append(node.name.value)

    def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef):
        class_name = self.class_stack.pop()

        if class_name in self.targets and isinstance(updated.body, IndentedBlock):
            new_body = self._process_block(updated.body, class_name)
            return updated.with_changes(body=new_body)

        return updated

    def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef):
        func_name = original.name.value

        if self.class_stack:
            qualified_class = ".".join(self.class_stack)
            key = f"{qualified_class}.{func_name}"
        else:
            key = func_name

        if key in self.targets and isinstance(updated.body, IndentedBlock):
            new_body = self._process_block(updated.body, key)
            return updated.with_changes(body=new_body)

        return updated
