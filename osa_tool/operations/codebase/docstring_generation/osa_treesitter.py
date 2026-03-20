import logging
import os
from pathlib import Path

import tree_sitter
import tree_sitter_python as tspython
from tree_sitter import Parser, Language


class OSA_TreeSitter(object):
    """
    Class for extracting and representing source code structure using tree-sitter parsing, enabling detailed analysis and transformation of code syntax and organization for downstream processing.
    
        Attributes:
            cwd: A current working directory with source code files.
    """


    def __init__(self, scripts_path: str, ignore_list: list[str] = None):
        """
        Initialization of the OSA_TreeSitter instance.
        
        Args:
            scripts_path: Path to the scripts directory provided by the user.
            ignore_list: Optional list of file names to ignore during processing. If not provided, defaults to ["__init__.py"].
        
        The method sets up the instance by storing the scripts path, initializing an empty import map, and configuring the ignore list. This prepares the instance for subsequent operations that will analyze or process files within the scripts directory while excluding specified files.
        """
        self.cwd = scripts_path
        self.import_map = {}
        if ignore_list:
            self.ignore_list = ignore_list
        else:
            self.ignore_list = ["__init__.py"]

    def files_list(self, path: str) -> tuple[list, 0] | tuple[list[str], 1]:
        """
        Returns a list of Python files from the provided path, along with a status code indicating the input type.
        
        If a directory path is provided, recursively walks through it to collect all `.py` files that are not ignored.
        If a single `.py` file path is provided, returns a list containing only that file.
        
        The status code indicates how the input was interpreted:
        - 0: A directory was provided (or an invalid file path was given).
        - 1: A valid `.py` file path was provided.
        
        This distinction is used internally by `_if_file_handler` to adjust subsequent processing.
        
        Args:
            path: A filesystem path pointing to either a directory or a `.py` file.
        
        Returns:
            A tuple containing:
                - A list of file paths (strings). If a directory was processed, the list contains all non-ignored `.py` files within it.
                  If a single file was provided, the list contains only that file's absolute path.
                  If the path is invalid or no matching files are found, an empty list is returned.
                - An integer status code (0 or 1) as described above.
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
        """
        Method checks if the current path is relative to any directory in the ignore list.
        
        WHY: This method is used to skip analysis of files or directories that should be excluded,
        such as build artifacts, dependencies, or user-specified directories, to focus processing
        only on relevant source code.
        
        Args:
            path: Path to the file being checked.
        
        Returns:
            True if the file is inside any ignored directory.
            False if the file is not inside any ignored directory.
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
        """
        Inner method returns the directory portion of a given file path.
        
        This is a class-level utility used to extract the head (parent directory) from a full file path. It is typically called when a status trigger (such as a file change or validation event) occurs, to isolate the directory for further processing—for example, to locate related scripts or resources within the same folder.
        
        Args:
            path: The full file path provided by the user.
        
        Returns:
            The head (directory portion) of the path.
        """
        return os.path.split(path)[0]

    @staticmethod
    def open_file(file: str) -> str:
        """
        Reads and returns the entire content of a specified file as a string.
        
        This static method provides a simple, consistent way to load text file contents
        with UTF-8 encoding, which is commonly used for source code and documentation files.
        Using UTF-8 ensures proper handling of international characters and symbols that
        may appear in modern codebases.
        
        Args:
            file: The path to the file to be read.
        
        Returns:
            The complete textual content of the file as a string.
        """
        content = None
        with open(file, encoding="utf-8", mode="r") as f:
            content = f.read()
        return content

    @staticmethod
    def _parser_build(filename: str) -> Parser | None:
        """
        Inner method builds the corresponding parser based on the file's extension.
        
        This method determines which language parser to instantiate by checking the file
        extension. Currently, it only supports Python files; other file types return None.
        This selective parsing allows the tool to focus on supported languages for
        documentation generation and code analysis.
        
        Args:
            filename: Name of the file found in the provided directory.
        
        Returns:
            A configured Parser object for Python files, or None if the file extension
            is not supported.
        """
        if filename.endswith(".py"):
            py_language = Language(tspython.language())
            return Parser(py_language)
        return None

    def _parse_source_code(self, filename: str) -> tuple[tree_sitter.Tree, str]:
        """
        Inner method parses the provided file with the source code.
        
        This method orchestrates the parsing of a source code file by first building a language-specific parser based on the file extension, then reading the file's content, and finally parsing that content to produce a syntax tree. This process is necessary to convert raw source code into a structured representation that can be analyzed for documentation generation and code understanding.
        
        Args:
            filename: The path to the source code file to be parsed.
        
        Returns:
            A tuple containing:
                - The tree-sitter syntax tree representing the parsed code structure.
                - The raw source code content of the file as a string.
        """
        parser: Parser = self._parser_build(filename)
        source_code: str = self.open_file(filename)
        return parser.parse(source_code.encode("utf-8")), source_code

    @staticmethod
    def _traverse_expression(class_attributes: list, expr_node: tree_sitter.Node) -> list:
        """
        Traverses an expression node and appends any identifiers found in assignment nodes to the class attributes list.
        
        This method is used to recursively extract attribute names (identifiers) from assignment statements within a class definition, supporting the documentation of class structure.
        
        Args:
            class_attributes: A list to which identifiers found in assignment nodes will be appended.
            expr_node: The expression node to be traversed, typically representing a block of code (e.g., within a class body).
        
        Returns:
            list: The updated class attributes list after traversing the expression node. The list is modified in place and also returned for convenience.
        """
        for node in expr_node.children:
            if node.type == "assignment":
                for child in node.children:
                    if child.type == "identifier":
                        class_attributes.append(child.text.decode("utf-8"))
        return class_attributes

    def _get_attributes(self, class_attributes: list, block_node: tree_sitter.Node) -> list:
        """
        Gets the attributes of a class by traversing a block node from a class body.
        
        This method iterates through the immediate children of the given block node. When a child node is an "expression_statement", it calls the internal `_traverse_expression` method to extract class attributes from that expression. This process is necessary because class attributes are often defined via assignment statements within the class body, which appear as expression statements in the parsed syntax tree.
        
        Args:
            class_attributes: A list of class attribute names that will be updated with any new attributes found.
            block_node: A tree-sitter node representing a block of code (typically the body of a class definition).
        
        Returns:
            list: The updated list of class attributes after processing all expression statements in the block node. The list is modified in-place and also returned for convenience.
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
        
        This method extracts the class name, start line, docstring, attributes, and methods from a syntax tree node representing a class definition. It populates the class's methods by processing both direct function definitions and those nested within the class's block node. The parsed details are appended to the provided structure dictionary under the "structure" key.
        
        Args:
            structure: A dictionary containing a "structure" list where the parsed class details will be appended, and an "imports" dictionary used for resolving method calls.
            source_code: A string of the source code that contains the class to be parsed.
            node: A tree_sitter.Node object that represents the class in the source code.
            dec_list: A list of decorators for the class. Defaults to an empty list.
        
        Returns:
            list: The updated "structure" list with the parsed class details appended. The list is modified in-place and also returned for convenience.
        
        Why:
        - The method processes both top-level function definitions and those inside a block node to ensure all methods are captured, as class methods can appear in either form in the syntax tree.
        - It extracts attributes and docstrings from the class body block to provide a complete representation of the class.
        - The imports dictionary from the structure is passed to method extraction to help resolve external method calls within the class's methods.
        """

        class_name = node.child_by_field_name("name").text.decode("utf-8")
        start_line = node.start_point[0] + 1
        class_methods = []
        class_attributes = []
        docstring = None

        for child in node.children:
            if child.type == "block":
                class_attributes = self._get_attributes(class_attributes, child)
                docstring = self._get_docstring(child)
                method_details = self._traverse_block(class_name, child, source_code, structure["imports"])
                class_methods.extend(method_details)

            if child.type == "function_definition":
                method_details = self._extract_function_details(
                    child, source_code, structure["imports"], class_name=class_name
                )
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
        
        This method processes a tree-sitter function definition node, extracts its detailed information via a helper, and appends a structured entry to the provided structure dictionary. It is used during repository analysis to build a comprehensive representation of functions for documentation generation.
        
        Args:
            structure: A dictionary containing the structural representation of the code, which includes an imports dictionary and a "structure" list to be updated.
            source_code: The source code of the file as a string.
            node: The tree-sitter Node representing the function definition.
            dec_list: A list of decorator names applied to the function. Defaults to an empty list.
        
        Returns:
            The updated structure dictionary with the function's details appended to the "structure" list. The appended entry is a dictionary containing:
                - type: Always "function".
                - start_line: The 1-indexed starting line number of the function in the source file.
                - details: A dictionary of extracted function details (name, arguments, docstring, method calls, etc.).
        
        Why:
        - The start_line is converted from tree-sitter's 0-based indexing to 1-based indexing for user-friendly reporting.
        - The method relies on a helper to extract comprehensive function metadata, which is then stored in a standardized format within the overall code structure.
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
        
        This method iterates through the children of a tree-sitter AST node, identifying decorators by their node types ("identifier" or "call"). Each identified decorator is formatted with an '@' prefix and appended to the provided list.
        
        Args:
            dec_list: The list to which decorators are to be appended.
            dec_node: The tree-sitter node from which decorators are to be extracted. The method expects this node to represent a decorator list in the AST.
        
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
        It handles both 'from ... import ...' and 'import ...' statements, including aliases (using 'as').
        The method only resolves paths for modules that exist as .py files within the current working directory (self.cwd);
        if a module is not found locally, it is omitted from the result.
        
        Args:
            import_text: A string containing a single import statement (e.g., "from module import Class" or "import module as alias").
        
        Returns:
            dict: A dictionary where each key is an alias (or the original name if no alias is given). For 'from ... import' statements,
                  each value is a dictionary with keys 'module', 'class', and 'path'. For 'import' statements (without 'from'),
                  each value is a dictionary with keys 'module' and 'path' (no 'class' key). Returns an empty dictionary if the input
                  is not a valid import statement, if parsing fails, or if no local module file is found.
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
        
        This method traverses the immediate children of the root node to find import statements.
        Only import statements that correspond to local Python files (within the current working directory)
        are included in the result; unresolved imports are omitted.
        
        Parameters:
            root_node: The root node from which to extract import statements.
        
        Returns:
            dict: A dictionary mapping imported module names (or aliases) to their resolved paths.
                  Each value is a dictionary containing 'module' and 'path' keys, and for 'from ... import'
                  statements also a 'class' key. Returns an empty dictionary if no valid local imports are found.
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
        - call_text: The full import call text that needs to be resolved (e.g., "my_module.MyClass.some_method").
        - call_alias: The alias used in the import call (e.g., "my_alias").
        - imports: A dictionary mapping import aliases to corresponding module/class data. Each entry should contain at least "module" and "path" keys, optionally a "class" key.
        - incantations: A dictionary containing alias substitutions for import resolution. If provided, it is used to remap the first part of call_text before lookup. (default None)
        
        Returns:
        A dictionary containing the resolved import information with the following keys:
        - "module": The module name extracted from imports data.
        - "class": The class name extracted from imports data if available; otherwise None.
        - "function": The function/method name extracted from the import call if available; None otherwise.
        - "path": The path to the module extracted from imports data.
        
        If the alias cannot be found in imports, an empty dictionary is returned.
        
        Notes:
        - The method first splits call_text at the first dot to isolate an alias. If incantations is provided and contains this alias, the alias is substituted.
        - If call_text contains no dot, the call_alias is mapped to the entire call_text in incantations (if incantations is provided), and no function/class details are extracted.
        - When rest text exists after the alias, the method parses it to determine class and function details:
            - If the first part ends with "()", it is treated as a class instantiation, and the class name is extracted.
            - Otherwise, the first part is treated as a function or attribute.
            - In case of chained method calls (multiple parts after the first dot), the entire chain is stored under the "function" key.
        - This resolution enables the OSA Tool to accurately trace and document dependencies and calls within analyzed source code.
        
        Example:
        resolved_import = OSA_TreeSitter._resolve_import("my_module.MyClass.some_method", "my_alias", imports_data)
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
        Extract all function calls from a function node, filtering by import resolvability.
        
        Returns only:
        - Regular functions: foo(), bar()
        - Self methods: self.method()
        - Class methods: ClassName.method()
        - Optionally: calls resolvable through imports (determined via _resolve_import)
        
        Excludes:
        - Nested calls within other calls (e.g., calls inside arguments)
        - Instance method calls: obj.method(), result.method()
        - Internal nested function calls (calls inside nested function definitions are skipped)
        - Calls from assignments that are not resolved to an import path
        
        Parameters:
            - function_node: The tree_sitter.Node representing the function node to analyze.
            - source_code: The source code of the function as a string, used to extract call text via byte offsets.
            - imports: A dictionary containing information about imports for resolution.
        
        Returns:
            list: A sorted list of unique function/method names being called from the function node.
            
        Why:
        - The method focuses on calls that are directly in the function body or resolvable via imports to identify dependencies and external interactions.
        - It excludes nested and instance calls to avoid overcounting and to maintain a clear view of top-level or importable dependencies.
        - Recursive traversal ensures all calls in the function block are captured, while skipping nested function definitions prevents internal calls from being included.
        - Assignment nodes are specially checked to capture imported class instantiations (e.g., `obj = SomeClass()`), linking them to import resolution.
        """
        function_calls = set()
        alias_map = {}

        block_node = next((child for child in function_node.children if child.type == "block"), None)
        if not block_node:
            return []

        def extract_calls_recursive(node):
            """Recursively extract calls from all nodes, including nested blocks."""
            # Skip nested function definitions
            if node.type == "function_definition" and node != function_node:
                return

            # Process call nodes
            if node.type == "call":
                call_target = node.child_by_field_name("function")
                if call_target:
                    call_text = source_code[call_target.start_byte : call_target.end_byte].strip()

                    # Filter out empty or invalid calls
                    if not call_text or call_text in ("", " "):
                        return

                    function_calls.add(call_text)

            # Check assignments for imported class instantiation
            elif node.type == "assignment":
                alias = None
                for subchild in node.children:
                    if subchild.type == "identifier":
                        alias = subchild.text.decode("utf-8")
                    elif subchild.type == "call":
                        call_target = subchild.child_by_field_name("function")
                        if call_target:
                            call_text = source_code[call_target.start_byte : call_target.end_byte].strip()
                            resolved = self._resolve_import(call_text, alias, imports, alias_map)
                            if resolved and resolved.get("path"):
                                function_calls.add(call_text)

            # Recursively process children
            for child in node.children:
                extract_calls_recursive(child)

        # Start recursive extraction from block node
        extract_calls_recursive(block_node)

        return sorted(list(function_calls))

    def extract_structure(self, filename: str) -> list:
        """
        Extracts the structural elements of a given source code file and returns them in a structured dictionary.
        
        This method parses the specified file to identify and catalog its top-level components: imports, functions, and classes (including their methods and attributes). It handles both plain definitions and definitions that are preceded by decorators. The resulting structure is used by the OSA Tool to generate comprehensive documentation and analyze repository organization.
        
        Args:
            filename: The path to the source code file to be analyzed.
        
        Returns:
            A dictionary containing two keys:
                - "imports": A dictionary mapping imported module names (or aliases) to their resolved paths, as extracted from the file's import statements.
                - "structure": A list of dictionaries, each representing a top-level function or class found in the file. Each entry includes details such as name, start line, docstring, and, for classes, their methods and attributes. Functions and classes that are decorated are recorded with their decorator list.
        
        Why:
        - The method distinguishes between decorated and non-decorated definitions because decorators (like `@staticmethod`) affect how the subsequent definition should be interpreted and documented.
        - It processes imports separately to enable later resolution of external references within the extracted structure.
        - The output is structured to support downstream tasks like automated documentation generation, code understanding, and repository enhancement within the OSA Tool pipeline.
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
        """
        Inner method to retrieve the docstring from a class or method node.
        
        This method extracts the first string literal found within a block node, which typically represents the docstring in Python source code. It is used to capture documentation strings for classes and methods during repository analysis.
        
        Args:
            block_node: A tree-sitter node representing a code block (e.g., class or method definition) that may contain a docstring.
        
        Returns:
            The decoded docstring as a string, or None if no docstring is found.
        """
        docstring = None
        for child in block_node.children:
            if child.type == "expression_statement":
                for c_c in child.children:
                    if c_c.type == "string":
                        docstring = c_c.text.decode("utf-8")
        return docstring

    def _traverse_block(self, class_name: str, block_node: tree_sitter.Node, source_code: bytes, imports: dict) -> list:
        """
        Inner method that traverses a "block" node in the parsed syntax tree to extract method definitions.
        
        This method processes the children of a block node (typically representing a class body) to identify both decorated and undecorated function definitions. For each function definition found, it extracts detailed method information via `_extract_function_details`. Decorated definitions are handled by first collecting decorators before extracting the function details.
        
        Args:
            class_name: The name of the containing class, used to annotate extracted method details.
            block_node: A tree-sitter node representing a block (e.g., a class body) that contains method definitions.
            source_code: The source code of the file as bytes, used to extract method source text.
            imports: Dictionary of import information from the file, used to resolve method calls during extraction.
        
        Returns:
            A list of dictionaries, each containing detailed information for one method (see `_extract_function_details` for structure).
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
                            dec_child, source_code, imports, dec_list, class_name
                        )
                        methods.append(method_details)

            if child.type == "function_definition":
                method_details = self._extract_function_details(child, source_code, imports, class_name=class_name)
                methods.append(method_details)
        return methods

    def _extract_function_details(
        self,
        function_node: tree_sitter.Node,
        source_code: str,
        imports: dict,
        dec_list: list = [],
        class_name: str = None,
    ) -> dict:
        """
        Extract detailed information from a function_definition node in the parsed syntax tree.
        
        This method processes a function or method node to extract its structural components,
        including its name, arguments, return type, source code, and related metadata. It is
        used during repository analysis to build a comprehensive representation of functions
        and methods for documentation generation.
        
        Args:
            function_node: The tree-sitter node representing a function or method definition.
            source_code: The source code of the file as a string (not bytes).
            imports: Dictionary containing import information for resolving method calls.
            dec_list: List of decorators applied to the function. Defaults to empty list.
            class_name: Name of the containing class if the function is a method; otherwise None.
        
        Returns:
            Dictionary containing:
                - class_name: Name of the containing class (or None for standalone functions)
                - method_name: Name of the function/method
                - decorators: List of decorator names
                - docstring: Extracted docstring if present
                - arguments: List of parameter names (including *args and **kwargs prefixes)
                - return_type: Return type annotation as string
                - start_line: Starting line number in the source file (1-indexed)
                - source_code: Full source code of the function
                - method_calls: Sorted list of unique function/method calls made within the function body
        
        Why:
        - The method decodes source bytes to UTF-8 strings because tree-sitter nodes store
          byte offsets, but the analysis requires text.
        - It handles various parameter patterns (typed, default, splat) to correctly extract
          argument names regardless of annotation style.
        - Method calls are resolved using import information to identify external dependencies
          and filter out unresolved or instance-based calls.
        - The docstring is extracted from the first string literal in the function's block,
          following Python convention.
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
                # Handle typed parameters (e.g., param: int)
                if param_node.type == "typed_parameter":
                    for typed_param_node in param_node.children:
                        if typed_param_node.type == "identifier":
                            arguments.append(typed_param_node.text.decode("utf-8"))
                # Handle typed parameters with defaults (e.g., param: int = 5)
                elif param_node.type == "typed_default_parameter":
                    for typed_param_node in param_node.children:
                        if typed_param_node.type == "identifier":
                            arguments.append(typed_param_node.text.decode("utf-8"))
                # Handle parameters with defaults but no type (e.g., param=None)
                elif param_node.type == "default_parameter":
                    for child in param_node.children:
                        if child.type == "identifier":
                            arguments.append(child.text.decode("utf-8"))
                            break  # Take only the first identifier (parameter name)
                # Handle **kwargs
                elif param_node.type == "dictionary_splat_pattern":
                    for child in param_node.children:
                        if child.type == "identifier":
                            arguments.append(f"**{child.text.decode('utf-8')}")
                            break
                # Handle *args
                elif param_node.type == "list_splat_pattern":
                    for child in param_node.children:
                        if child.type == "identifier":
                            arguments.append(f"*{child.text.decode('utf-8')}")
                            break
                # Handle simple identifiers (e.g., param)
                elif param_node.type == "identifier":
                    arguments.append(param_node.text.decode("utf-8"))

        source_bytes = source_code.encode("utf-8")
        source = source_bytes[function_node.start_byte : node.end_byte].decode("utf-8")

        return_node = function_node.child_by_field_name("return_type")
        return_type = None
        if return_node:
            return_type = source_code[return_node.start_byte : return_node.end_byte]

        method_calls = self._resolve_method_calls(function_node, source_code, imports)

        return {
            "class_name": class_name,
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
        """
        Analyzes a directory or a single Python file, extracting structural information from each `.py` file found.
        
        Args:
            path: A filesystem path to a directory or a single `.py` file. If a directory is provided, all non-ignored `.py` files within it are processed recursively.
        
        Returns:
            A dictionary where each key is a filename (string) and each value is the extracted structural dictionary for that file. The structure includes imports and top-level definitions (functions and classes) as returned by `extract_structure`. If the path is invalid or contains no `.py` files, an empty dictionary is returned.
        
        Why:
        - The method distinguishes between directory and file inputs to handle both bulk analysis of a project and targeted analysis of a single script.
        - It filters for `.py` files because the structural extraction is specific to Python source code.
        - The internal status flag from `files_list` determines whether to update the current working directory, which is used for relative path resolution in subsequent processing steps.
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
        """
        Method logs out the results of the directory analysis.
        
        Args:
            results: dictionary containing a filename and its source code's structure.
                Each key is a filename, and each value is a dictionary with a "structure" key.
                The structure is a list of items, where each item is either a class or a function.
                For classes, the item includes the class name, start line, docstring, and a list of methods.
                For functions, the item includes details such as the function name, arguments, return type, start line, docstring, and source code.
        
        WHY: This method provides a human-readable log of the analyzed source code structure, making it easier to review the extracted classes, functions, methods, and their associated metadata (like docstrings and source code) for debugging or verification purposes.
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
        """
        Logs the results of the directory analysis into "examples/report.txt".
        
        Creates a structured report summarizing the analyzed source code, including classes, functions, methods, their docstrings, and source code snippets. The report is saved in a fixed location relative to the current working directory.
        
        Args:
            results: A dictionary mapping filenames to their parsed source code structures. Each entry is expected to contain a "structure" key with a list of items representing classes or functions.
        
        Why:
            This method provides a human-readable summary of the analysis for review or debugging purposes. It outputs details such as class and method signatures, line numbers, docstrings, and source code excerpts to help verify the accuracy of the parsed structure.
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

    @staticmethod
    def build_function_index(results: dict) -> dict:
        """
        Build an index of all functions and methods for quick lookup by name.
        
        This allows retrieving source code of called functions without storing it in every reference. The index includes both standalone functions and class methods, with methods indexed under both their simple name and a 'class.method' format for unambiguous access.
        
        Args:
            results: Dictionary returned from analyze_directory() containing the parsed structure. Each key is a filename, and each value contains the 'structure' list of parsed items (classes and functions).
        
        Returns:
            A dictionary mapping function names to their full details. For each entry, the value is a dictionary containing the original details from the parsed structure (such as 'source_code', 'arguments', 'docstring', 'return_type', 'start_line', etc.) augmented with metadata:
            - For a class method: two entries are created: one under the method's simple name and another under 'class_name.method_name'. Both include the original method details plus 'file' and 'class' keys.
            - For a standalone function: one entry is created under the function name, including the original details plus a 'file' key.
            The returned dictionary has the form:
            {
                'function_name': { ...details..., 'file': 'path/to/file.py' },
                'class_name.method_name': { ...details..., 'file': 'path/to/file.py', 'class': 'class_name' },
                ...
            }
        """
        function_index = {}

        for filename, structures in results.items():
            for item in structures["structure"]:
                if item["type"] == "class":
                    class_name = item["name"]
                    for method in item["methods"]:
                        method_name = method["method_name"]
                        # Store both simple name and class.method format
                        full_method_name = f"{class_name}.{method_name}"

                        function_index[method_name] = {
                            **method,
                            "file": filename,
                            "class": class_name,
                        }
                        function_index[full_method_name] = {
                            **method,
                            "file": filename,
                            "class": class_name,
                        }

                elif item["type"] == "function":
                    details = item["details"]
                    func_name = details["method_name"]

                    function_index[func_name] = {
                        **details,
                        "file": filename,
                    }

        return function_index
