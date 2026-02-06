import logging
import os
from pathlib import Path

import tree_sitter
import tree_sitter_python as tspython
from tree_sitter import Parser, Language


class OSA_TreeSitter(object):
    """Class for the extraction of the source code's structure to be processed later by LLM.

    Attributes:
        cwd: A current working directory with source code files.
    """

    def __init__(self, scripts_path: str, ignore_list: list[str] = None):
        """Initialization of the instance based on the provided path to the scripts.

        Args:
            scripts_path: provided by user path to the scripts.
        """
        self.cwd = scripts_path
        self.import_map = {}
        if ignore_list:
            self.ignore_list = ignore_list
        else:
            self.ignore_list = ["__init__.py"]

    def files_list(self, path: str) -> tuple[list, 0] | tuple[list[str], 1]:
        """Method provides a list of files occurring in the provided path.

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
                    p = Path(os.path.join(root, file)).resolve()
                    if file.endswith(".py") and not self._is_ignored(p) and p.name not in self.ignore_list:
                        script_files.append(os.path.join(root, file))
            return script_files, 0

        elif os.path.isfile(path) and path.endswith(".py"):
            return [os.path.abspath(path)], 1

        return [], 0

    def _is_ignored(self, path: Path) -> bool:
        """Method checks if current path is relative to any of the ignore list.

        Args:
            path: path to the script file.

        Returns:
            True: file is relative to the ignored path.
            False: file is not relative to the ignored path.
        """
        for dir in self.ignore_list:
            ignore_path = Path(os.path.join(self.cwd, dir)).resolve()
            try:
                path.relative_to(ignore_path)
                return True
            except ValueError:
                continue
        return False

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

    @staticmethod
    def _parser_build(filename: str) -> Parser | None:
        """Inner method builds the corresponding parser based on file's extension.

        Args:
            filename: name of the file occured in the provided directory.

        Returns:
            Compiled parser.
        """
        if filename.endswith(".py"):
            py_language = Language(tspython.language())
            return Parser(py_language)
        return None

    def _parse_source_code(self, filename: str) -> tuple[tree_sitter.Tree, str]:
        """Inner method parses the provided file with the source code.

        Args:
            filename: name of the file occured in the provided directory.

        Returns:
            Tuple containing tree structure of the code and source code.
        """
        parser: Parser = self._parser_build(filename)
        source_code: str = self.open_file(filename)
        return parser.parse(source_code.encode("utf-8")), source_code

    @staticmethod
    def _traverse_expression(class_attributes: list, expr_node: tree_sitter.Node) -> list:
        """
        Traverses an expression node and appends any identifiers found in assignment nodes to the class attributes list.

        Args:
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

    def _get_attributes(self, class_attributes: list, block_node: tree_sitter.Node) -> list:
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
        structure: dict[dict, list],
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
                method_details = self._traverse_block(child, source_code, structure["imports"])
                class_methods.extend(method_details)

            if child.type == "function_definition":
                method_details = self._extract_function_details(child, source_code, structure["imports"])
                class_methods.append(method_details)

        structure["structure"].append(
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

    def _function_parser(
        self,
        structure: dict[dict, list],
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
        method_details = self._extract_function_details(node, source_code, structure["imports"], dec_list)
        start_line = node.start_point[0] + 1  # convert 0-based to 1-based indexing
        structure["structure"].append(
            {
                "type": "function",
                "start_line": start_line,
                "details": method_details,
            }
        )

    @staticmethod
    def _get_decorators(dec_list: list, dec_node: tree_sitter.Node) -> list:
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

    def _resolve_import_path(self, import_text: str):
        """
        Resolve import path from given import text.

        This method resolves the import path of entities specified in the import_text. It extracts the module name,
        entity names, and their corresponding paths in case they are found in the current working directory.

        Parameters:
            - import_text: The import text containing import statements to be resolved.

        Returns:
            dict: A dictionary containing the import mappings where keys are alias names and values are dictionaries
                  with 'module', 'class', and 'path' keys indicating the imported module, class, and path respectively.
        """
        import_mapping = {}

        if "import " in import_text or "from " in import_text:
            import_text = import_text.strip()

            if import_text.startswith("from"):
                try:
                    from_part, import_part = import_text.split("import", 1)
                except ValueError:
                    return import_mapping

                module_name = from_part.replace("from", "").strip()
                imported_entities = [entity.strip() for entity in import_part.split(",")]

                module_path = None
                possible_path = os.path.join(self.cwd, *module_name.split(".")) + ".py"
                if os.path.exists(possible_path):
                    module_path = possible_path

                for entity in imported_entities:
                    if " as " in entity:
                        imported_name, alias_name = [e.strip() for e in entity.split(" as ", 1)]
                    else:
                        imported_name = entity
                        alias_name = imported_name
                    if module_path:
                        import_mapping[alias_name] = {
                            "module": module_name,
                            "class": imported_name,
                            "path": module_path,
                        }

            elif import_text.startswith("import"):
                parts = import_text.replace("import", "").strip().split()
                if "as" in parts:
                    idx = parts.index("as")
                    module_name = parts[0]
                    alias_name = parts[idx + 1]
                else:
                    module_name = parts[0]
                    alias_name = module_name

                module_path = None
                possible_path = os.path.join(self.cwd, *module_name.split(".")) + ".py"
                if os.path.exists(possible_path):
                    module_path = possible_path

                if module_path:
                    import_mapping[alias_name] = {
                        "module": module_name,
                        "path": module_path,
                    }

        return import_mapping

    def _extract_imports(self, root_node: tree_sitter.Node):
        """
        Extracts import statements from the given root node and returns a dictionary mapping imported
        module names to their resolved paths.

        Parameters:
            root_node: The root node from which to extract import statements.

        Returns:
            dict: A dictionary mapping imported module names to their resolved paths.
        """
        import_map = {}
        for node in root_node.children:
            if node.type in ("import_statement", "import_from_statement"):
                import_text = node.text.decode("utf-8")
                resolved_imports = self._resolve_import_path(import_text)
                import_map.update(resolved_imports)
        return import_map

    @staticmethod
    def _resolve_import(call_text: str, call_alias: str, imports: dict, incantations: dict = None) -> dict:
        """
        Resolves an import call to retrieve module/class information based on provided imports and aliases.

        Parameters:
        - call_text: The full import call text that needs to be resolved.
        - call_alias: The alias used in the import call.
        - imports: A dictionary mapping import aliases to corresponding module/class data.
        - incantations: A dictionary containing any alias substitutions for import resolution. (default None)

        Returns:
        A dictionary containing the resolved import information with the following keys:
        - "module": The module name extracted from imports data.
        - "class": The class name extracted from imports data if available.
        - "function": The function/method name extracted from the import call if available, None otherwise.
        - "path": The path to the module extracted from imports data.

        Note:
        - In case of a chained method call, the "function" key will hold the entire method call string.

        Example:
        resolved_import = self._resolve_import("my_module.MyClass.some_method", "my_alias", imports_data)
        """
        # Split at the first dot to get alias and the rest of the call
        if "." in call_text:
            alias, rest = call_text.split(".", 1)
            if incantations and alias in incantations.keys():
                alias = incantations[alias]
        else:
            incantations[call_alias] = call_text
            alias, rest = call_text, None

        # Retrieve module/class info from imports
        imports_data = imports.get(alias)
        if not imports_data:
            return {}

        resolved_import = {
            "module": imports_data["module"],
            "class": imports_data.get("class"),
            "function": None,
            "path": imports_data["path"],
        }

        if rest:
            parts = rest.split(".")

            if "()" in parts[0]:
                class_name = parts[0].replace("()", "")
                resolved_import["class"] = class_name

                if len(parts) > 1:
                    resolved_import["function"] = parts[1]  # Get method name after class
            else:
                resolved_import["function"] = parts[0]  # Direct function call

            # Handle chained methods
            if len(parts) > 1:
                resolved_import["function"] = ".".join(parts)

        return resolved_import

    def _resolve_method_calls(self, function_node: tree_sitter.Node, source_code: str, imports: dict) -> list:
        """
        Resolve method calls in the given function node and return a list of resolved method calls.

        Parameters:
            - function_node: The tree_sitter.Node representing the function node to analyze.
            - source_code: The source code of the function as a string.
            - imports: A dictionary containing information about imports.

        Returns:
            list: A list of resolved method calls extracted from the function node.
        """
        method_calls = []
        alias_map = {}

        def process_call(call_node: tree_sitter.Node, alias=None):
            call_target = call_node.child_by_field_name("function")
            if not call_target:
                return

            call_text = source_code[call_target.start_byte : call_target.end_byte]
            resolved_call = self._resolve_import(call_text, alias, imports, alias_map)
            if resolved_call:
                method_calls.append(resolved_call)

        block_node = next((child for child in function_node.children if child.type == "block"), None)
        if not block_node:
            return []

        for expr in block_node.children:
            if not expr.children:
                continue

            for node in expr.children:
                # Handle assignment statements
                if node.type == "assignment":
                    alias = None
                    call_node = None

                    for child in node.children:
                        if child.type == "identifier":
                            alias = child.text.decode("utf-8")
                        elif child.type == "call":
                            call_node = child

                    if call_node:
                        process_call(call_node, alias)

                elif node.type == "call":
                    process_call(node)

        return method_calls

    def extract_structure(self, filename: str) -> list:
        """Method extracts the structure of the occured file in the provided directory.

        Args:
            filename: name of the file occured in the provided directory.

        Returns:
            List containing occurring in file functions, classes, their start lines and methods
        """
        structure = {}
        structure["structure"] = []
        tree, source_code = self._parse_source_code(filename)
        root_node = tree.root_node
        imports = self._extract_imports(root_node)
        structure["imports"] = imports
        for node in root_node.children:
            if node.type == "decorated_definition":
                dec_list = []
                for dec_node in node.children:
                    if dec_node.type == "decorator":
                        dec_list = self._get_decorators(dec_list, dec_node)

                    elif dec_node.type == "class_definition":
                        self._class_parser(structure, source_code, dec_node, dec_list)

                    elif dec_node.type == "function_definition":
                        self._function_parser(structure, source_code, dec_node, dec_list)

            elif node.type == "function_definition":
                self._function_parser(structure, source_code, node)

            elif node.type == "class_definition":
                self._class_parser(structure, source_code, node)

        return structure

    @staticmethod
    def _get_docstring(block_node: tree_sitter.Node) -> str:
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

    def _traverse_block(self, block_node: tree_sitter.Node, source_code: bytes, imports: dict) -> list:
        """Inner method traverses occurring in file's tree structure "block" node.

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
                        method_details = self._extract_function_details(dec_child, source_code, imports, dec_list)
                        methods.append(method_details)

            if child.type == "function_definition":
                method_details = self._extract_function_details(child, source_code, imports)
                methods.append(method_details)
        return methods

    def _extract_function_details(
        self,
        function_node: tree_sitter.Node,
        source_code: str,
        imports: dict,
        dec_list: list = [],
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

        source_bytes = source_code.encode("utf-8")
        source = source_bytes[function_node.start_byte : node.end_byte].decode("utf-8")

        return_node = function_node.child_by_field_name("return_type")
        return_type = None
        if return_node:
            return_type = source_code[return_node.start_byte : return_node.end_byte]

        method_calls = self._resolve_method_calls(function_node, source_code, imports)

        return {
            "method_name": method_name,
            "decorators": dec_list,
            "docstring": docstring,
            "arguments": arguments,
            "return_type": return_type,
            "start_line": start_line,
            "source_code": source,
            "method_calls": method_calls,
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
        """Method logs out the results of the directory analyze.

        Args:
            results: dictionary containing a filename and its source code's structure.
        """
        logging.info(f"The provided path: '{self.cwd}'")
        for filename, structures in results.items():
            logging.info(f"File: {filename}")
            for item in structures["structure"]:
                if item["type"] == "class":
                    logging.info(f"  - Class: {item['name']}, line {item['start_line']}")
                    if item["docstring"]:
                        logging.info(f"      Docstring: {item['docstring']}")
                    for method in item["methods"]:
                        logging.info(
                            f"      - Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}"
                        )
                        if method["docstring"]:
                            logging.info(f"          Docstring:\n        {method['docstring']}")
                        logging.info(f"        Source:\n{method['source_code']}")
                elif item["type"] == "function":
                    details = item["details"]
                    logging.info(
                        f"  - Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}"
                    )
                    if details["docstring"]:
                        logging.info(f"          Docstring:\n    {details['docstring']}")
                    logging.info(f"        Source:\n{details['source_code']}")

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
                for item in structures["structure"]:
                    if item["type"] == "class":
                        f.write(f"----Class: {item['name']}, line {item['start_line']}\n")
                        if item["docstring"]:
                            f.write(f"    Docstring:\n    {item['docstring']}\n")
                        for method in item["methods"]:
                            f.write(
                                f"--------Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}\n"
                            )
                            if method["docstring"]:
                                f.write(f"        Docstring:\n        {method['docstring']}\n")
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
