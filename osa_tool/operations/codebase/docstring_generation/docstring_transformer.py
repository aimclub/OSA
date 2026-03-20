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
        """
        Initializes a DocstringTransformer instance.
        
        Args:
            generated_docstrings: A dictionary of generated docstrings categorized by type (e.g., "methods", "functions", "classes").
            source_lines: The source code lines of the file being processed.
            default_indent: The default indentation string to use for formatting docstrings during insertion.
        
        Initializes the following instance attributes:
            generated_docstrings (dict): Stores the provided dictionary of generated docstrings.
            source_lines (List[str]): Stores the provided source code lines.
            default_indent (str): Stores the provided default indentation string.
            targets (dict[str, str]): A mapping of target identifiers (e.g., "ClassName.methodName") to their generated docstrings, built by `_build_targets`. This mapping is created during initialization to efficiently associate each docstring with its specific target (function, method, or class) for later insertion or validation.
            class_stack (list[str]): A stack used to track nested class names during processing, which helps in constructing correct target identifiers for methods within nested classes.
        """
        self.generated_docstrings = generated_docstrings
        self.source_lines = source_lines
        self.default_indent = default_indent
        self.targets: dict[str, str] = self._build_targets()
        self.class_stack: list[str] = []

    def _escape_triple_quotes(self, text: str) -> str:
        """
        Escapes triple quotes in a string by replacing them with escaped versions.
        This is necessary to safely embed triple-quoted strings (e.g., docstrings) inside other triple-quoted strings without causing premature termination.
        
        Args:
            text: The input string containing triple quotes to escape.
        
        Returns:
            The modified string with triple quotes escaped.
        """
        return text.replace('"""', r"\"\"\"")

    def _escape_backslashes(self, text: str) -> str:
        """
        Escapes backslashes in the given text by replacing each single backslash with two backslashes.
        This is necessary to ensure backslashes are properly represented in generated documentation, especially when the text will be written to files or used in contexts where a single backslash could be interpreted as an escape character.
        
        Args:
            text: The input string containing backslashes to escape.
        
        Returns:
            The modified string with escaped backslashes.
        """
        return text.replace("\\", "\\\\")

    def _get_body_indent(self, node: cst.CSTNode) -> str:
        """
        Calculates the indentation string for the body of a function or class.
        
        WHY: This method ensures that the body of a function or class is indented consistently relative to its definition, preserving the original formatting style of the source code.
        
        Args:
            node: The CST node representing the function or class definition.
        
        Returns:
            The indentation string to be used for the body of the node. This is derived by taking the indentation of the definition line and appending a default indent. If position metadata is unavailable, only the default indent is returned.
        """
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
        """
        Correct indentation formatting for docstring literals.
        
        This method processes a raw docstring text by:
        1. Stripping surrounding quotes and whitespace
        2. Escaping triple quotes to prevent premature termination when embedded in another triple-quoted string
        3. Escaping backslashes to ensure proper representation in generated documentation
        4. Applying consistent indentation to each line of the content
        
        Args:
            text: The raw docstring text (including surrounding quotes).
            indent: The indentation string to apply to each non-empty line.
        
        Returns:
            A properly formatted triple-quoted string with correct indentation and escaped special characters.
        """
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
        """
        Builds a mapping of target identifiers to generated docstrings.
        
        This method iterates over the generated docstrings stored in `self.generated_docstrings`,
        which are categorized by type ("methods", "functions", "classes"). For each category,
        it constructs a unique key for each docstring and adds it to the mapping. The mapping is
        used to associate each generated docstring with its specific target (e.g., a method within
        a class) for later insertion or validation.
        
        Args:
            None.
        
        Returns:
            dict[str, str]: A dictionary where keys are identifiers and values are the
            corresponding generated docstrings. For methods, the key format is
            "ClassName.methodName". For functions, the key is the function name. For classes,
            the key is the class name. The values are the raw docstring text.
        """
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
        """
        Creates a docstring node from a text string with proper indentation.
        
        This method constructs an AST node representing a docstring, ensuring the text is correctly formatted and indented for insertion into Python source code. It delegates detailed formatting (like escaping quotes and applying line-by-line indentation) to a helper method.
        
        Args:
            text: The raw docstring text content, typically including surrounding quotes.
            indent: The indentation string (e.g., spaces or tabs) to apply to each line of the docstring.
        
        Returns:
            A SimpleStatementLine node containing the formatted docstring as an expression.
        """
        doc_value = self._format_docstring_literal(text, indent)
        return SimpleStatementLine(body=[Expr(value=SimpleString(doc_value))])

    def _has_docstring(self, body: Sequence[cst.BaseStatement]) -> bool:
        """
        Checks whether the given body of statements starts with a docstring.
        
        Why: This method is used to detect docstrings at the beginning of a function, class, or module body, which is necessary for documentation processing and transformation tasks in the OSA Tool.
        
        Args:
            body: Sequence of statements to examine.
        
        Returns:
            True if the first statement is a simple statement line containing a single expression that is a simple string (i.e., a docstring), otherwise False.
        """
        return (
            body
            and isinstance(body[0], SimpleStatementLine)
            and len(body[0].body) == 1
            and isinstance(body[0].body[0], Expr)
            and isinstance(body[0].body[0].value, SimpleString)
        )

    def visit_Module(self, node: cst.Module):
        """
        Visits a Module node and initializes module-level state required for subsequent transformations.
        
        This method is called when the transformer begins processing a LibCST Module node. It captures the root module and its default indentation style, establishing the foundational context for consistent code formatting and manipulation throughout the transformation process.
        
        Args:
            node: The Module node being visited.
        
        Initializes the following instance attributes:
            module: The Module node being visited. Stored to provide global access to the root of the syntax tree during transformation.
            current_indent: The default indentation string for the module (e.g., four spaces or a tab). Used to maintain consistent indentation in generated or modified code.
        """
        self.module = node
        self.current_indent = node.default_indent

    def _process_block(self, block: IndentedBlock, key: str, indent: str) -> IndentedBlock:
        """
        Processes an indented block by adding or replacing its docstring.
        
        Why: This method is used to update the documentation of a code block (e.g., a function or class) by either inserting a new docstring or replacing an existing one, ensuring consistent and properly formatted documentation as part of the OSA Tool's automated documentation enhancement.
        
        Args:
            block: The indented block to process.
            key: Key used to retrieve the target docstring text from the transformer's internal targets mapping.
            indent: Indentation string (e.g., spaces) to apply to each line of the new docstring, preserving the block's formatting.
        
        Returns:
            A new IndentedBlock with the updated docstring. The original block is not modified; changes are applied to a copy of its body.
        """
        body = list(block.body)
        new_doc = self._make_doc(self.targets[key], indent)

        if self._has_docstring(body):
            body[0] = new_doc
        else:
            body.insert(0, new_doc)

        return block.with_changes(body=tuple(body))

    def visit_ClassDef(self, node: cst.ClassDef):
        """
        Visits a ClassDef node and updates the class stack.
        
        Args:
            node: The ClassDef node being visited.
        
        Note:
            This method appends the current class name to `self.class_stack` to maintain a record of the class hierarchy during AST traversal. This stack is used to track nesting and context when processing other nodes within the class scope.
        """
        self.class_stack.append(node.name.value)

    def leave_ClassDef(self, original: cst.ClassDef, updated: cst.ClassDef):
        """
        Processes a class definition node after its children have been visited.
        
        WHY: This method ensures that docstrings for targeted classes are updated after all child nodes (e.g., methods, nested classes) have been processed, allowing any internal transformations to complete before modifying the class-level documentation.
        
        Args:
            original: The original class definition node before any transformations.
            updated: The class definition node after its children have been visited.
        
        Returns:
            The potentially updated class definition node. If the class name is a target and its body is an IndentedBlock, the body is processed to update its docstring, and the node is returned with the new body. Otherwise, the node is returned unchanged.
        """
        class_name = self.class_stack.pop()

        if class_name in self.targets and isinstance(updated.body, IndentedBlock):
            indent = self._get_body_indent(original)
            new_body = self._process_block(updated.body, class_name, indent)
            return updated.with_changes(body=new_body)

        return updated

    def leave_FunctionDef(self, original: cst.FunctionDef, updated: cst.FunctionDef):
        """
        Processes a FunctionDef node upon leaving it during tree traversal, potentially updating its body with a docstring.
        
        WHY: This method is part of the automated documentation enhancement process. It checks if the current function (or method, if nested in a class) is a target for docstring addition or replacement. If so, it modifies the function's body to include the new docstring, ensuring consistent and properly formatted documentation is added to the source code.
        
        Args:
            original: The original CST node for the function definition before any child transformations.
            updated: The updated CST node for the function definition after its children have been visited and potentially modified.
        
        Returns:
            The potentially updated CST FunctionDef node. If the function is identified as a target (based on its qualified name matching a key in the transformer's targets), and its body is an IndentedBlock, returns a node with a body modified to include the new docstring. Otherwise, returns the input `updated` node unchanged.
        """
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
