import os
from os import listdir
from os.path import isfile, join
import tree_sitter
from tree_sitter import Parser, Language
import tree_sitter_python as tspython


class OSA_TreeSitter(object):
    """Class for the extraction of the source code's structure to be processed later by LLM.

    Attributes:
        cwd: A current working directory with source code files.
    """

    def __init__(self, scripts_path: str):
        """Initialization of the instance based on the provided path to the scripts.

        Args:
            scripts_path: provided by user path to the scripts.
        """
        self.cwd = scripts_path

    @staticmethod
    def files_list(path: str) -> tuple[list, 0] | tuple[list[str], 1]:
        """Method provides a list of files occuring in the provided path.

        If user provided a path to a file with a particular extension
        the method returns a corresponding status which will trigger
        inner "_if_file_handler" method to cut the path's tail.

        Args:
            path: provided by user path to the scripts.

        Returns:
            A tuple containing a list of files in the provided directory
            and status for a specific file usecase. Statuses:
            0 - a directory was provided
            1 - a path to the specific file was provided.
        """
        script_files = []

        if os.path.isdir(path):
            for root, _, files in os.walk(path):
                for file in files:
                    if file.endswith(".py"):
                        script_files.append(os.path.join(root, file))
            return script_files, 0

        elif os.path.isfile(path) and path.endswith(".py"):
            return ([os.path.abspath(path)], 1)

        return ([], 0)

    @classmethod
    def _if_file_handler(cls, path: str) -> str:
        """Inner method returns a path's head if status trigger occured.

        Args:
            path: provided by user path to the scripts.

        Returns:
            Path's head.
        """
        return os.path.split(path)[0]

    @staticmethod
    def open_file(file: str) -> str:
        """Method reads the content of the occured file.

        Args:
            file: file occured in the provided directory.

        Returns:
            Read content.
        """
        content = None
        with open(file, encoding="utf-8", mode="r") as f:
            content = f.read()
        return content

    def _parser_build(self, filename: str) -> Parser:
        """Inner method builds the corresponding parser based on file's extension.

        Args:
            filename: name of the file occured in the provided directory.

        Returns:
            Compiled parser.
        """
        if filename.endswith(".py"):
            PY_LANGUAGE = Language(tspython.language())
            return Parser(PY_LANGUAGE)

    def _parse_source_code(self, filename: str) -> tuple[tree_sitter.Tree, str]:
        """Inner method parses the provided file with the source code.

        Args:
            filename: name of the file occured in the provided directory.

        Returns:
            Tuple containing tree structure of the code and source code.
        """
        parser: Parser = self._parser_build(filename)
        source_code: str = self.open_file(filename)
        return (parser.parse(source_code.encode("utf-8")), source_code)

    def _traverse_expression(
        self, class_attributes: list, expr_node: tree_sitter.Node
    ) -> list:
        """
        Traverses an expression node and appends any identifiers found in assignment nodes to the class attributes list.

        Args:
            self: The instance of the class.
            class_attributes: A list to which identifiers found in assignment nodes will be appended.
            expr_node: The expression node to be traversed.

        Returns:
            list: The updated class attributes list after traversing the expression node.
        """
        for node in expr_node.children:
            if node.type == "assignment":
                for child in node.children:
                    if child.type == "identifier":
                        class_attributes.append(child.text.decode("utf-8"))
        return class_attributes

    def _get_attributes(
        self, class_attributes: list, block_node: tree_sitter.Node
    ) -> list:
        """
        Gets the attributes of a class.

        This method traverses the children of a given block node and if the node type is "expression_statement",
        it calls the _traverse_expression method to get the class attributes.

        Args:
            class_attributes: A list of class attributes.
            block_node: A node in the tree_sitter.

        Returns:
            list: The updated list of class attributes after traversing the block node.
        """
        for node in block_node.children:
            if node.type == "expression_statement":
                class_attributes = self._traverse_expression(class_attributes, node)

        return class_attributes

    def _class_parser(
        self,
        structure: list,
        source_code: str,
        node: tree_sitter.Node,
        dec_list: list = [],
    ) -> list:
        """
        Parses a class from the source code and appends its details to the given structure.

        Args:
            structure: A list where the parsed class details will be appended.
            source_code: A string of the source code that contains the class to be parsed.
            node: A tree_sitter.Node object that represents the class in the source code.
            dec_list: A list of decorators for the class. Defaults to an empty list.

        Returns:
            list: The updated structure list with the parsed class details appended."""

        class_name = node.child_by_field_name("name").text.decode("utf-8")
        start_line = node.start_point[0] + 1
        class_methods = []
        class_attributes = []
        docstring = None

        for child in node.children:
            if child.type == "block":
                class_attributes = self._get_attributes(class_attributes, child)
                docstring = self._get_docstring(child)
                method_details = self._traverse_block(child, source_code)
                for method in method_details:
                    class_methods.append(method)

            if child.type == "function_definition":
                method_details = self._extract_function_details(child, source_code)
                class_methods.append(method_details)

        structure.append(
            {
                "type": "class",
                "name": class_name,
                "decorators": dec_list,
                "start_line": start_line,
                "docstring": docstring,
                "attributes": class_attributes,
                "methods": class_methods,
            }
        )

        return structure

    def _function_parser(
        self,
        structure: list,
        source_code: str,
        node: tree_sitter.Node,
        dec_list: list = [],
    ) -> list:
        """
        Parses a function node and extracts its details to update the structure.

        Parameters:
            - self: The instance of the class.
            - structure: A list containing the structure details of the code.
            - source_code: The source code of the function.
            - node: The tree-sitter Node representing the function.
            - dec_list: A list of decorators for the function (default=[]).

        Returns:
            A list containing the updated structure with the function details added.
        """
        method_details = self._extract_function_details(node, source_code, dec_list)
        start_line = node.start_point[0] + 1  # convert 0-based to 1-based indexing
        structure.append(
            {
                "type": "function",
                "start_line": start_line,
                "details": method_details,
            }
        )

        return structure

    def _get_decorators(self, dec_list: list, dec_node: tree_sitter.Node) -> list:
        """
        Extracts decorators from a given node and appends them to a list.

        Args:
            dec_list: The list to which decorators are to be appended.
            dec_node: The node from which decorators are to be extracted.

        Returns:
            list: The updated list with appended decorators.
        """
        for decorator in dec_node.children:
            if decorator.type == "identifier" or decorator.type == "call":
                dec_list.append(f'@{decorator.text.decode("utf-8")}')

        return dec_list

    def extract_structure(self, filename: str) -> list:
        """Method extracts the structure of the occured file in the provided directory.

        Args:
            filename: name of the file occured in the provided directory.

        Returns:
            List containing occuring in file functions, classes, their start lines and methods
        """
        structure = []
        tree, source_code = self._parse_source_code(filename)
        root_node = tree.root_node
        for node in root_node.children:
            if node.type == "decorated_definition":
                dec_list = []
                for dec_node in node.children:
                    if dec_node.type == "decorator":
                        dec_list = self._get_decorators(dec_list, dec_node)

                    elif dec_node.type == "class_definition":
                        structure = self._class_parser(
                            structure, source_code, dec_node, dec_list
                        )

                    elif dec_node.type == "function_definition":
                        structure = self._function_parser(
                            structure, source_code, dec_node, dec_list
                        )

            elif node.type == "function_definition":
                structure = self._function_parser(structure, source_code, node)

            elif node.type == "class_definition":
                structure = self._class_parser(structure, source_code, node)

        return structure

    def _get_docstring(self, block_node: tree_sitter.Node) -> str:
        """Inner method to retrieve class or method's docstring.

        Args:
            block_node: an occured block node, containing class's methods.

        Returns:
            List of function/method's details.
        """
        docstring = None
        for child in block_node.children:
            if child.type == "expression_statement":
                for c_c in child.children:
                    if c_c.type == "string":
                        docstring = c_c.text.decode("utf-8")
        return docstring

    def _traverse_block(self, block_node: tree_sitter.Node, source_code: bytes) -> list:
        """Inner method traverses occuring in file's tree structure "block" node.

        Args:
            block_node: an occured block node, containing class's methods.
            source_code: source code of the file in bytes.

        Returns:
            List of function/method's details.
        """
        methods = []
        for child in block_node.children:
            if child.type == "decorated_definition":
                dec_list = []
                for dec_child in child.children:
                    if dec_child.type == "decorator":
                        dec_list = self._get_decorators(dec_list, dec_child)

                    if dec_child.type == "function_definition":
                        method_details = self._extract_function_details(
                            dec_child, source_code, dec_list
                        )
                        methods.append(method_details)

            if child.type == "function_definition":
                method_details = self._extract_function_details(child, source_code)
                methods.append(method_details)
        return methods

    def _extract_function_details(
        self, function_node: tree_sitter.Node, source_code: str, dec_list: list = []
    ) -> dict:
        """Inner method extracts the details of "function_definition" node in file's tree structure.

        Args:
            function_node: an occured block node, containing class's methods details.
            source_code: source code of the file in bytes.

        Returns:
            Dictionary containing method's/function's name, args, return type, start line
            and source code.
        """
        method_name = function_node.child_by_field_name("name").text.decode("utf-8")
        start_line = function_node.start_point[0] + 1

        docstring = None
        for node in function_node.children:
            if node.type == "block":
                docstring = self._get_docstring(node)

        parameters_node = function_node.child_by_field_name("parameters")
        arguments = []
        if parameters_node:
            for param_node in parameters_node.children:
                if param_node.type == "typed_parameter":
                    for typed_param_node in param_node.children:
                        if typed_param_node.type == "identifier":
                            arguments.append(typed_param_node.text.decode("utf-8"))
                if param_node.type == "typed_default_parameter":
                    for typed_param_node in param_node.children:
                        if typed_param_node.type == "identifier":
                            arguments.append(typed_param_node.text.decode("utf-8"))
                if param_node.type == "identifier":
                    arguments.append(param_node.text.decode("utf-8"))

        source_code_start = function_node.start_byte
        source_code_end = function_node.end_byte
        source = source_code[source_code_start:source_code_end]

        return_node = function_node.child_by_field_name("return_type")
        return_type = None
        if return_node:
            return_type = source_code[return_node.start_byte : return_node.end_byte]

        return {
            "method_name": method_name,
            "decorators": dec_list,
            "docstring": docstring,
            "arguments": arguments,
            "return_type": return_type,
            "start_line": start_line,
            "source_code": source,
        }

    def analyze_directory(self, path: str) -> dict:
        """Method analyzes provided directory.

        Args:
            path: provided by user path to the scripts.

        Returns:
            Dictionary containing a filename and its source code's structure.
        """
        results = {}
        files_list, status = self.files_list(path)
        if status:
            self.cwd = OSA_TreeSitter._if_file_handler(path)
        for filename in files_list:
            if filename.endswith(".py"):
                structure = self.extract_structure(filename)
                results[filename] = structure
        return results

    def show_results(self, results: dict) -> None:
        """Method prints out the results of the directory analyze.

        Args:
            results: dictionary containing a filename and its source code's structure.
        """
        print(f"The provided path: '{self.cwd}'")
        for filename, structures in results.items():
            print(f"File: {filename}")
            for item in structures:
                if item["type"] == "class":
                    print(f"  - Class: {item['name']}, line {item['start_line']}")
                    if item["docstring"]:
                        print(f"      Docstring: {item['docstring']}")
                    for method in item["methods"]:
                        print(
                            f"      - Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}"
                        )
                        if method["docstring"]:
                            print(
                                f"          Docstring:\n        {method['docstring']}"
                            )
                        print(f"        Source:\n{method['source_code']}")
                elif item["type"] == "function":
                    details = item["details"]
                    print(
                        f"  - Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}"
                    )
                    if details["docstring"]:
                        print(f"          Docstring:\n    {details['docstring']}")
                    print(f"        Source:\n{details['source_code']}")
        print()

    def log_results(self, results: dict) -> None:
        """Method logs the results of the directory analyze into "examples/report.txt".

        Args:
            results: dictionary containing a filename and its source code's structure.
        """
        os.makedirs("examples", exist_ok=True)
        with open("examples/report.txt", "w", encoding="utf-8") as f:
            f.write(f"The provided path: '{self.cwd}'\n")
            for filename, structures in results.items():
                f.write(f"File: {filename}\n")
                for item in structures:
                    if item["type"] == "class":
                        f.write(
                            f"----Class: {item['name']}, line {item['start_line']}\n"
                        )
                        if item["docstring"]:
                            f.write(f"    Docstring:\n    {item['docstring']}\n")
                        for method in item["methods"]:
                            f.write(
                                f"--------Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}\n"
                            )
                            if method["docstring"]:
                                f.write(
                                    f"        Docstring:\n        {method['docstring']}\n"
                                )
                            f.write(f"        Source:\n    {method['source_code']}\n")
                    elif item["type"] == "function":
                        details = item["details"]
                        f.write(
                            f"----Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}\n"
                        )
                        if details["docstring"]:
                            f.write(f"    Docstring:\n    {details['docstring']}\n")
                        f.write(f"        Source:\n    {details['source_code']}\n")
                f.write("\n")
