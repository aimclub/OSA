import os
from os import listdir
from os.path import isfile, join
import tree_sitter
from tree_sitter import Parser, Language
import tree_sitter_python as tspython

class OSA_TreeSitter(object):

    def __init__(self, scripts_path: str):
        self.cwd = scripts_path
        self.script_files = self.files_list(self.cwd)

    @staticmethod
    def files_list(path: str) -> str:
        try:
            return ([file for file in listdir(path) if isfile(join(path, file))], 0)
        except NotADirectoryError:
            if path.endswith(".py"):
                return ([os.path.basename(os.path.normpath(path))], 1)
    
    @classmethod
    def _if_file_handler(cls, path: str):
        return os.path.split(path)[0]

    @staticmethod
    def open_file(path: str, file: str) -> bytes:
        content = None
        with open(os.path.join(path, file), 'rb') as f:
            content = f.read()
        return content

    def _parser_build(self, filename: str) -> Parser:
        if(filename.endswith(".py")):
            PY_LANGUAGE = Language(tspython.language())
            return Parser(PY_LANGUAGE)

    def _parse_source_code(self, filename: str):
        parser: Parser = self._parser_build(filename)
        source_code: bytes = self.open_file(self.cwd, filename)
        return parser.parse(source_code), source_code

    def extract_methods(self, filename: str):
        structure = []
        tree, source_code = self._parse_source_code(filename)
        root_node = tree.root_node
        for node in root_node.children:
            if node.type == "function_definition":
                method_details = self._extract_function_details(node, source_code)
                start_line = node.start_point[0] + 1 #convert 0-based to 1-based indexing
                structure.append({'type': "function", "start_line": start_line, "details": method_details})

            elif node.type == "class_definition":
                class_name = node.child_by_field_name("name").text.decode("utf-8")
                start_line = node.start_point[0] + 1
                class_methods = []

                for child in node.children:
                    if child.type == "block":
                        method_details = self._traverse_block(child, source_code)
                        for method in method_details:
                            class_methods.append(method)
            
                    if child.type == "function_definition":
                        method_details = self._extract_function_details(child, source_code)
                        class_methods.append(method_details)

                structure.append({"type": "class", "name": class_name, "start_line": start_line, "methods": class_methods})

        return structure
    
    def _traverse_block(self, block_node: tree_sitter.Node, source_code: bytes):
        methods = []
        for child in block_node.children:
            if child.type == "decorated_definition":
                for dec_child in child.children:
                    if dec_child.type == "function_definition":
                        method_details = self._extract_function_details(dec_child, source_code)
                        methods.append(method_details)

            if child.type == "function_definition":
                method_details = self._extract_function_details(child, source_code)
                methods.append(method_details)
        return methods
    
    def _extract_function_details(self, function_node: tree_sitter.Node, source_code: bytes):
        method_name = function_node.child_by_field_name("name").text.decode("utf-8")
        start_line = function_node.start_point[0] + 1
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
        
        return_node = function_node.child_by_field_name("return_type")
        return_type = None
        if return_node:
            return_type = source_code[return_node.start_byte:return_node.end_byte].decode("utf-8")
        
        return {
            "method_name": method_name,
            "arguments": arguments,
            "return_type": return_type,
            "start_line": start_line,
        }

    def analyze_directory(self, path: str):
        results = {}
        files_list, status = self.files_list(path)
        if status:
            self.cwd = OSA_TreeSitter._if_file_handler(path)
        for filename in files_list:
            if filename.endswith(".py"):
                structure = self.extract_methods(filename)
                results[filename] = structure
        return results
    
    def show_results(self, results: dict):
        print(f"The provided path: '{self.cwd}'")
        for filename, structures in results.items():
            print(f"File: {filename}")
            for item in structures:
                if item["type"] == "class":
                    print(f"  - Class: {item['name']}, line {item['start_line']}")
                    for method in item["methods"]:
                        print(f"      - Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}")
                elif item["type"] == "function":
                    details = item["details"]
                    print(f"  - Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}")
        print()

    def log_results(self, results: dict):
        os.makedirs("examples",exist_ok = True)
        with open("examples/report.txt", 'w') as f:
            f.write(f"The provided path: '{self.cwd}'\n")
            for filename, structures in results.items():
                f.write(f"File: {filename}\n")
                for item in structures:
                    if item["type"] == "class":
                        f.write(f"  - Class: {item['name']}, line {item['start_line']}\n")
                        for method in item["methods"]:
                            f.write(f"      - Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}\n")
                    elif item["type"] == "function":
                        details = item["details"]
                        f.write(f"  - Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}\n")
                f.write("\n")