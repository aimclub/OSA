import libcst as cst
from libcst import (
    CSTTransformer,
    SimpleStatementLine,
    Expr,
    SimpleString,
    IndentedBlock,
)
from typing import Sequence, List
from libcst.metadata import PositionProvider


class DocstringTransformer(CSTTransformer):
    """
    Transformer to insert/update docstrings,
    by built qualified targets.
    """

    METADATA_DEPENDENCIES = (PositionProvider,)

    def __init__(self, generated_docstrings: dict, source_lines: List[str], default_indent: str):
        self.generated_docstrings = generated_docstrings
        self.source_lines = source_lines
        self.default_indent = default_indent
        self.targets: dict[str, str] = self._build_targets()
        self.class_stack: list[str] = []

    def _escape_triple_quotes(self, text: str) -> str:
        return text.replace('"""', r"\"\"\"")

    def _escape_backslashes(self, text: str) -> str:
        return text.replace("\\", "\\\\")

    def _get_body_indent(self, node: cst.CSTNode) -> str:
        pos = self.get_metadata(PositionProvider, node, None)
        if not pos:
            return self.default_indent

        # line with function/class definition
        line = self.source_lines[pos.start.line - 1]
        # indent to def/class
        prefix = line[: pos.start.column]
        # concating default indent for body
        return prefix + self.default_indent

    def _format_docstring_literal(self, text: str, indent: str) -> str:
        """correct indentation formatting"""
        clean = text.strip('"').strip()

        clean = self._escape_triple_quotes(clean)
        clean = self._escape_backslashes(clean)

        lines = clean.split("\n")

        inner_lines = []
        for line in lines:
            if line.strip():
                inner_lines.append(indent + line)
            else:
                inner_lines.append("")

        inner = "\n".join(inner_lines)

        return f'"""\n{inner}\n{indent}"""'

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
                        targets[f["method_name"]] = docstring

                case "classes":
                    for docstring, c in generated:
                        targets[c] = docstring

        return targets

    def _make_doc(self, text: str, indent: str) -> SimpleStatementLine:
        doc_value = self._format_docstring_literal(text, indent)
        return SimpleStatementLine(body=[Expr(value=SimpleString(doc_value))])

    def _has_docstring(self, body: Sequence[cst.BaseStatement]) -> bool:
        return (
            body
            and isinstance(body[0], SimpleStatementLine)
            and len(body[0].body) == 1
            and isinstance(body[0].body[0], Expr)
            and isinstance(body[0].body[0].value, SimpleString)
        )

    def visit_Module(self, node: cst.Module):
        self.module = node
        self.current_indent = node.default_indent

    def _process_block(self, block: IndentedBlock, key: str, indent: str) -> IndentedBlock:
        body = list(block.body)
        new_doc = self._make_doc(self.targets[key], indent)

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
            indent = self._get_body_indent(original)
            new_body = self._process_block(updated.body, class_name, indent)
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
            indent = self._get_body_indent(original)
            new_body = self._process_block(updated.body, key, indent)
            return updated.with_changes(body=new_body)

        return updated
