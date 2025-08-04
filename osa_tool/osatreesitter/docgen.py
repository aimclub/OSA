import multiprocessing.pool
import os
import re
import textwrap
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import List, Dict, Any

import black
from pathlib import Path
import shutil
import subprocess

import black.report
import dotenv
import tiktoken
import yaml

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.utils import logger, osa_project_root

dotenv.load_dotenv()


class DocGen(object):
    """
    This class is a utility for generating Python docstrings using OpenAI's GPT model. It includes methods
    for generating docstrings for a class, a single method, formatting the structure of Python files,
    counting the number of tokens in a given prompt, extracting the docstring from GPT's response,
    inserting a generated docstring into the source code and also processing a Python file by generating
    and inserting missing docstrings.

    Methods:
        __init__(self)
            Initializes the class instance by setting the 'api_key' attribute to the value of the
            'OPENAI_API_KEY' environment variable.

        format_structure_openai(structure)
            Formats the structure of Python files in a readable string format by iterating over the given
            'structure' dictionary and generating a formatted string.

        count_tokens(prompt, model)
            Counts the number of tokens in a given prompt using a specified model.

        generate_class_documentation(class_details, model)
            Generates documentation for a class using OpenAI GPT.

        generate_method_documentation()
            Generates documentation for a single method using OpenAI GPT.

        extract_pure_docstring(gpt_response)
            Extracts only the docstring from the GPT-4 response while keeping triple quotes.

        insert_docstring_in_code(source_code, method_details, generated_docstring)
            Inserts a generated docstring into the specified location in the source code.

        insert_cls_docstring_in_code(source_code, class_details, generated_docstring)
            Inserts a generated class docstring into the class definition and returns the updated source code.

        process_python_file(parsed_structure, file_path)
            Processes a Python file by generating and inserting missing docstrings and updates the source file
            with the new docstrings.

        generate_documentation_openai(file_structure, model)
            Generates the documentation for a given file structure using OpenAI's API by traversing the given
            file structure and for each class or standalone function, generating its documentation.
    """

    def __init__(self, config_loader: ConfigLoader):
        """
        Instantiates the object of the class.

        This method is a constructor that initializes the object by setting the 'api_key' attribute to the value of the 'OPENAI_API_KEY' environment variable.
        """
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.main_idea = None

    @staticmethod
    def format_structure_openai(structure: dict) -> str:
        """
        Formats the structure of Python files in a readable string format.

        This method iterates over the given dictionary 'structure' and generates a formatted string where it describes
        each file, its classes and functions along with their details such as line number, arguments, return type,
        source code and docstrings if available.

        Args:
            structure: A dictionary containing details of the Python files structure. The dictionary should
            have filenames as keys and values as lists of dictionaries. Each dictionary in the list represents a
            class or function and should contain keys like 'type', 'name', 'start_line', 'docstring', 'methods'
            (for classes), 'details' (for functions) etc. Each 'methods' or 'details' is also a dictionary that
            includes detailed information about the method or function.

        Returns:
            A formatted string representing the structure of the Python files.
        """
        formatted_structure = "The following is the structure of the Python files:\n\n"

        for filename, structures in structure.items():
            formatted_structure += f"File: {filename}\n"
            for item in structures:
                if item["type"] == "class":
                    formatted_structure += DocGen._format_class(item)
                elif item["type"] == "function":
                    formatted_structure += DocGen._format_function(item)

        return formatted_structure

    @staticmethod
    def format_structure_openai_short(filename: str, structure: dict) -> str:
        formatted_structure = "The following is the structure of the Python file:\n\n"

        structures = structure["structure"]
        if not structures:
            return ""
        formatted_structure += f"File: {filename}\n"
        for item in structures:
            if item["type"] == "class":
                formatted_structure += DocGen._format_class_short(item)
            elif item["type"] == "function":
                formatted_structure += DocGen._format_function_short(item)

        return formatted_structure

    @staticmethod
    def _format_class(item: dict) -> str:
        """Formats class details."""
        class_str = f"  - Class: {item['name']}, line {item['start_line']}\n"
        if item["docstring"]:
            class_str += f"      Docstring: {item['docstring']}\n"
        for method in item["methods"]:
            class_str += DocGen._format_method(method)
        return class_str

    @staticmethod
    def _format_method(method: dict) -> str:
        """Formats method details."""
        method_str = f"      - Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}\n"
        if method["docstring"]:
            method_str += f"          Docstring:\n        {method['docstring']}\n"
        method_str += f"        Source:\n{method['source_code']}\n"
        return method_str

    @staticmethod
    def _format_function(item: dict) -> str:
        """Formats function details."""
        details = item["details"]
        function_str = f"  - Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}\n"
        if details["docstring"]:
            function_str += f"          Docstring:\n    {details['docstring']}\n"
        function_str += f"        Source:\n{details['source_code']}\n"
        return function_str

    @staticmethod
    def _format_class_short(item: dict) -> str:
        """Formats class details."""
        class_str = f"  - Class: {item['name']}\n"
        if item["docstring"]:
            try:
                doc = item["docstring"].split("\n\n")[0].strip('"\n ')
                class_str += f"          Docstring:   {doc}\n"
            except:
                class_str += f"          Docstring:  {item['docstring']}\n"
        return class_str

    @staticmethod
    def _format_function_short(item: dict) -> str:
        """Formats function details."""
        details = item["details"]
        function_str = f"  - Function: {details['method_name']}\n"
        if details["docstring"]:
            try:
                doc = details["docstring"].split("\n\n")[0].strip('"\n ')
                function_str += f"          Docstring:\n    {doc}\n"
            except:
                function_str += f"          Docstring:\n    {details['docstring']}\n"
        return function_str

    def count_tokens(self, prompt: str) -> int:
        """
        Counts the number of tokens in a given prompt using a specified model.

        Args:
            prompt: The text for which to count the tokens.

        Returns:
            The number of tokens in the prompt.
        """
        enc = tiktoken.encoding_for_model(self.config.llm.model)
        tokens = enc.encode(prompt)
        return len(tokens)

    def generate_class_documentation(self, class_details: dict) -> str:
        """
        Generate documentation for a class.

        Args:
            class_details: A list of dictionaries containing method names and their docstrings.

        Returns:
            The generated class docstring.
        """
        # Construct a structured prompt
        prompt = (
            f"""Generate a single Python docstring for the following class {class_details[0]}. The docstring should follow Google-style format and include:\n"""
            "- A short summary of what the class does.\n"
            "- A list of its methods without details if class has them otherwise do not mention a list of methods.\n"
            "- A list of its attributes that explicitly mentioned at the constructor method's docstring (can be adressed as attributes, properties, class fields, etc.), without types if class or constructor method has them otherwise do not mention a list of attributes.\n"
            "- A brief summary of what its methods and attributes do if one has them for.\n\n"
            "Return only docstring without any quotation. Follow such format:\n <triple_quotes>\ncontent\n<triple_quotes>"
        )

        if len(class_details[1]) > 0:
            prompt += f"\nClass Attributes:\n"
            for attr in class_details[1]:
                prompt += f"- {attr}\n"

        if len(class_details[2:-1]) > 0:
            prompt += f"\nClass Methods:\n"
            for method in class_details[2:-1]:
                prompt += f"- {method['method_name']}: {method['docstring']}\n"

        return self.model_handler.send_request(prompt)

    def update_class_documentation(self, class_details: dict) -> str:
        """
        Generate documentation for a class.

        Args:
            class_details: A list of dictionaries containing method names and their docstrings.

        Returns:
            The generated class docstring.
        """
        # Construct a structured prompt
        try:
            desc, other = class_details[-1].split("\n\n", maxsplit=1)
            desc = desc.replace('"', "")
        except:
            return class_details[-1]

        old_desc = desc.strip('"\n ')
        prompt = (
            f"""Update the provided description for the following Python class {class_details[0]} using provided main idea of the project.\n"""
            """Do not pay too much attention to the provided main idea - try not to mention it explicitly.\n"""
            f"""The main idea: {self.main_idea}\n"""
            f"""Old docstring description part: {old_desc}\n\n"""
            """Return only pure changed description - without any code, other parts of docs, any quotations)"""
        )
        new_desc = self.model_handler.send_request(prompt)
        return "\n\n".join(['"""\n' + new_desc, other])

    def generate_method_documentation(self, method_details: dict, context_code: str = None) -> str:
        """
        Generate documentation for a single method.
        """
        prompt = (
            "Generate a Python docstring for the following method. The docstring should follow Google-style format and include:\n"
            "- A short summary of what the method does\n."
            "- A description of its parameters without types.\n"
            "- If the method is a class constructor, explicitly list all class fields (object properties) that are initialized, including their names and purposes. These fields should match the attributes assigned within the constructor (e.g., this.field = ..., self.field = ...). This information will be used to generate the class-level documentation.\n"
            "- The return type and description.\n"
            f"- Method Name: {method_details['method_name']}\n"
            "Method source code: You are given only the body of a single method, without its signature. All visible code, including any inner functions or nested logic, belongs to this single method. Do not write separate docstrings for inner functions — they are part of the main method's logic.\n"
            "```\n"
            f"""{method_details['source_code']}\n"""
            "```\n"
            "-List of arguments:\n"
            f"""{method_details['arguments']}\n"""
            f"""{"- Use provided source code of imported methods, functions to describe their usage." if context_code else ""}\n"""
            "Method Details:\n"
            f"- Method decorators: {method_details['decorators']}\n"
            f"""{"- Imported methods source code:" if context_code else ""}\n"""
            f"""{context_code if context_code else ""}\n\n"""
            "Note: DO NOT RETURN METHOD'S BODY. DO NOT count parameters which are not listed in the parameters list. DO NOT lose any parameter. DO NOT wrap any sections of the docstring into <any_tag> clear those parts out."
            "Return only docstring without any quotation. Follow such format:\n <triple_quotes>\ncontent\n<triple_quotes>"
        )

        return self.model_handler.send_request(prompt)

    def update_method_documentation(
        self, method_details: dict, context_code: str = None, class_name: str = None
    ) -> str:
        """
        Generate documentation for a single method.
        """
        docstring = method_details["docstring"]
        prompt = (
            """Update the provided docstring description for the following Python method using the main idea of the project.\n"""
            """Do not pay too much attention to the provided main idea - try not to mention it explicitly\n"""
            """Based on the provided context and main idea give an answer to the question WHY method doing what it is doing\n"""
            """If original docstring provides only description update it with Args and Return sections based on provided source code as well\n"""
            f"""Original docstring: {docstring}\n\n"""
            f"""{"- Use provided source code of imported methods, functions to understand their usage." if context_code else ""}\n"""
            """Method Details:\n"""
            f"""- Method Name: {method_details["method_name"]} {("located inside " + class_name + " class") if class_name else ""}\n"""
            f"""- Method decorators: {method_details["decorators"]}\n"""
            "- Source Code:\n"
            "```\n"
            f"""{method_details["source_code"]}\n"""
            "```\n"
            f"""{"- Imported methods source code:" if context_code else ""}\n"""
            f"""{context_code if context_code else ""}\n\n"""
            f"The main idea: {self.main_idea}\n"
            "Return only pure changed docstring - DO NOT RETURN ANY CODE, DO NOT RETURN other parts of docs"
        )
        new_desc = self.model_handler.send_request(prompt)

        return new_desc

    def extract_pure_docstring(self, gpt_response: str) -> str:
        """
        Extracts only the docstring from the GPT response while keeping triple quotes.
        Handles common formatting issues like Markdown blocks, extra indentation, and missing closing quotes.

        Args:
            gpt_response: Full response string from LLM.

        Returns:
            A properly formatted Python docstring string with triple quotes.
        """
        response = gpt_response.strip().replace("<triple quotes>", '"""')

        # 1 — Strip Markdown-style code block
        markdown_match = re.search(r"```[a-z]*\n([\s\S]+?)\n```", response, re.IGNORECASE)
        if markdown_match:
            response = markdown_match.group(1).strip()

        # 2 — Fix case: opening triple quote but no closure
        if response.count('"""') == 1:
            pos = response.find('"""')
            body = response[pos + 3 :].strip()
            if len(body.split()) > 3:
                return f'"""\n{body}\n"""'

        # 3 — Try to extract proper triple-quoted block
        match = re.search(r'("""|\'\'\')\n?(.*?)\n?\1', response, re.DOTALL)
        if match:
            quote = match.group(1)
            content = match.group(2).strip()

            # Remove accidental leaked `def ...():`
            content = re.sub(r"^\s*def\s+\w+\(.*?\):\s*", "", content, flags=re.MULTILINE).strip()

            # De-indent "Args" section
            if "Args" in content:
                spaces = re.findall(r"\n([^\S\r\n]*)Args", content)
                if spaces:
                    indent = spaces[0]
                    content = content.replace("\n" + indent, "\n")

            return f"{quote}\n{content}\n{quote}"

        # 4 — fallback: treat entire content as docstring if long enough
        if response.startswith("'''") and response.endswith("'''"):
            response = f'"""{response[3:-3].strip()}"""'
        cleaned = response.strip("`'\" \n")
        if len(cleaned.split()) > 3:
            return f'"""\n{cleaned}\n"""'

        return '"""No valid docstring found."""'

    @staticmethod
    def strip_docstring_from_body(body: str) -> str:
        """
        Method to trimm method's body from docstring
        """
        lines = body.strip().splitlines()
        if len(lines) < 1:
            return body

        first_line = lines[0].strip()
        if first_line.startswith(('"""', "'''")):
            closing = first_line[:3]
            # Oneliner docstring
            if first_line.count(closing) == 2:
                return "\n".join(lines[1:]).lstrip()
            # Multyline docstring
            for i in range(1, len(lines)):
                if closing in lines[i]:
                    return "\n".join(lines[i + 1 :]).lstrip()
        return body

    def insert_docstring_in_code(
        self, source_code: str, method_details: dict, generated_docstring: str, class_method: bool = False
    ) -> str:
        """
        Inserts or replaces a method-level docstring in the provided source code,
        using the method's body from method_details['source_code'] to locate the method.
        Handles multi-line signatures, decorators, async definitions, and existing docstrings.
        """
        method_body = self.strip_docstring_from_body(method_details["source_code"].strip())
        docstring_clean = self.extract_pure_docstring(generated_docstring)

        # Find method within a source code
        match = re.search(re.escape(method_details["source_code"]), source_code)
        if not match:
            return source_code
        body_start = match.start()

        if not body_start:
            return source_code

        start = body_start

        while start > 0 and source_code[start - 1] in " \t\n":
            start -= 1

        end = body_start + len(method_body)

        method_block = source_code[start:end]
        method_lines = method_block.splitlines(keepends=True)

        indent = "        " if class_method else "    "

        def indent_docstring(docstring: str) -> str:
            lines = docstring.strip().splitlines()
            if len(lines) == 1:
                return f'{indent}"""{lines[0]}"""'
            indented = [f"{indent}" + lines[0]]
            for line in lines[1:]:
                indented.append(f"{indent}{line}")
            return "\n".join(indented) + "\n"

        # Check for existing docstring right after signature
        signature_end_index = None
        for i, line in enumerate(method_lines):
            if line.strip().endswith(":"):
                signature_end_index = i
                break

        docstring_inserted = indent_docstring(docstring_clean)

        if signature_end_index is not None:
            next_line_index = signature_end_index + 1
            while next_line_index < len(method_lines) and method_lines[next_line_index].strip() == "":
                next_line_index += 1

            if next_line_index < len(method_lines) and method_lines[next_line_index].strip().startswith(('"""', "'''")):
                # Replace old docstring
                closing = method_lines[next_line_index].strip()[:3]
                end_doc_idx = next_line_index
                for j in range(next_line_index + 1, len(method_lines)):
                    if closing in method_lines[j]:
                        end_doc_idx = j
                        break
                method_lines = method_lines[:next_line_index] + [docstring_inserted] + method_lines[end_doc_idx + 1 :]
            else:
                # Insert new docstring
                method_lines.insert(signature_end_index + 1, docstring_inserted)

        updated_block = "".join(method_lines)
        result = source_code[:start] + updated_block + source_code[end:]

        return result

    def insert_cls_docstring_in_code(self, source_code: str, class_name: str, generated_docstring: str) -> str:
        """
        Inserts or replaces a class-level docstring for a given class name.

        Args:
            source_code: The full source code string.
            class_name: Name of the class to update.
            generated_docstring: The new docstring (raw response from LLM).

        Returns:
            Updated source code with the inserted or replaced class docstring.
        """
        class_pattern = (
            rf"(class\s+{class_name}\s*(\([^)]*\))?\s*:\n)"  # group 1: class signature
            rf"([ \t]*)"  # group 3: indentation (for docstring)
            rf"(\"\"\"[\s\S]*?\"\"\"|\'\'\'[\s\S]*?\'\'\')?"  # group 4: existing docstring (optional)
        )

        match = re.search(class_pattern, source_code)
        if not match:
            return source_code  # Class not found

        signature = match.group(1)
        indent = match.group(3) or "    "
        existing_docstring = match.group(4)

        docstring = self.extract_pure_docstring(generated_docstring)

        # Applying indentation to all docstring lines
        indented_lines = [indent + line if line.strip() else indent for line in docstring.strip().splitlines()]
        indented_docstring = "\n".join(indented_lines) + "\n"

        start, end = match.span()

        if existing_docstring:
            # Substituting an existing docstring
            updated_code = source_code[:start] + signature + indented_docstring + source_code[end:]
        else:
            # Inserting new docstring
            insert_point = source_code.find("\n", start) + 1
            updated_code = source_code[:insert_point] + indented_docstring + source_code[insert_point:]

        return updated_code

    def context_extractor(self, method_details: dict, structure: dict) -> str:
        """
            Extracts the context of method calls and functions from given method_details and code structure.

            Parameters:
            - method_details: A dictionary containing details about the method calls.
            - structure: A dictionary representing the code structure.

            Returns:
            A string containing the context of the method calls and functions in the format:
            - If a method call is found:
              "# Method {method_name} in class {class_name}
        {source_code}"
            - If a function call is found:
              "# Function {class_name}
        {source_code}"

            Note:
            - This method iterates over the method calls in method_details and searches for the corresponding methods and functions
              in the code structure. It constructs the context of the found methods and functions by appending their source code
              along with indicator comments.
            - The returned string contains the structured context of all the detected methods and functions.
        """

        def is_target_class(item, call):
            return item["type"] == "class" and item["name"] == call["class"]

        def is_target_method(method, call):
            return method["method_name"] == call["function"]

        def is_constructor(method, call):
            return method["method_name"] == "__init__" and call["function"] is None

        def is_target_function(item, call):
            return item["type"] == "function" and item["details"]["method_name"] == call["class"]

        context = []

        for call in method_details.get("method_calls", []):
            file_data = structure.get(call["path"], {})
            if not file_data:
                continue

            for item in file_data.get("structure", []):
                if is_target_class(item, call):
                    for method in item.get("methods", []):
                        if is_target_method(method, call) or is_constructor(method, call):
                            method_name = call["function"] if call["function"] else "__init__"
                            context.append(
                                f"# Method {method_name} in class {call['class']}\n" + method.get("source_code", "")
                            )
                elif is_target_function(item, call):
                    context.append(f"# Function {call['class']}\n" + item["details"].get("source_code", ""))

        return "\n".join(context)

    def format_with_black(self, filename):
        """
        Formats a Python source code file using the `black` code formatter.

        This method takes a filename as input and formats the code in the specified file using the `black` code formatter.

        Parameters:
            - filename: The path to the Python source code file to be formatted.

        Returns:
            None
        """
        black.format_file_in_place(
            Path(filename),
            fast=True,
            mode=black.FileMode(),
            write_back=black.WriteBack.YES,
        )

    def process_python_file(self, parsed_structure: dict) -> None:
        """
        Processes a Python file by generating and inserting missing docstrings.

        This method iterates over the given parsed structure of a Python codebase, checks each class method for missing
        docstrings, and generates and inserts them if missing. The method updates the source file with the new docstrings
        and logs the path of the updated file.

        Args:
            parsed_structure: A dictionary representing the parsed structure of the Python codebase.
                The dictionary keys are filenames and the values are lists of dictionaries representing
                classes and their methods.

        Returns:
            None
        """

        for filename, structure in parsed_structure.items():
            if not structure["structure"]:
                logger.info(f"File {filename} does not contain any functions, methods or class constructions.")
                continue
            self._process_one_file(filename, structure, project_structure=parsed_structure)

    def _process_one_file(self, filename, file_structure, project_structure):
        with open(filename, "r", encoding="utf-8") as f:
            source_code = f.read()
        for item in file_structure["structure"]:
            if item["type"] == "class":
                for method in item["methods"]:
                    if method["docstring"] == None or self.main_idea:  # If docstring is missing
                        logger.info(
                            f"""{"Generating" if self.main_idea else "Updating"} docstring for the method: {method['method_name']} of class {item['name']} at {filename}"""
                        )
                        method_context = self.context_extractor(method, project_structure)
                        generated_docstring = (
                            self.generate_method_documentation(method, method_context)
                            if self.main_idea is None
                            else self.update_method_documentation(method, method_context, class_name=item["name"])
                        )
                        if not generated_docstring:
                            logger.info(
                                f"Failed to recieve a proper docstring for the method {method['method_name']} of class {item['name']}.\nRetrying ..."
                            )
                            generated_docstring = (
                                self.generate_method_documentation(method, method_context)
                                if self.main_idea is None
                                else self.update_method_documentation(method, method_context, class_name=item["name"])
                            )
                        if generated_docstring:
                            generated_docstring = self.extract_pure_docstring(generated_docstring)
                            method["docstring"] = generated_docstring
                            source_code = self.insert_docstring_in_code(
                                source_code, method, generated_docstring, class_method=True
                            )
                        else:
                            logger.error(f"Could not recieve any response from the LLM.")
            if item["type"] == "function":
                func_details = item["details"]
                if func_details["docstring"] == None or self.main_idea:
                    logger.info(
                        f"""{"Generating" if self.main_idea else "Updating"} docstring for the function: {func_details['method_name']} at {filename}"""
                    )
                    generated_docstring = (
                        self.generate_method_documentation(func_details)
                        if self.main_idea is None
                        else self.update_method_documentation(func_details)
                    )
                    if not generated_docstring:
                        logger.info(
                            f"Failed to recieve a proper docstring for the function {func_details['method_name']} at {filename}.\nRetrying ..."
                        )
                        generated_docstring = (
                            self.generate_method_documentation(func_details)
                            if self.main_idea is None
                            else self.update_method_documentation(func_details)
                        )
                    if generated_docstring:
                        generated_docstring = self.extract_pure_docstring(generated_docstring)
                        source_code = self.insert_docstring_in_code(source_code, func_details, generated_docstring)
                    else:
                        logger.error(f"Could not recieve any response from the LLM.")

        for item in file_structure["structure"]:
            if item["type"] == "class" and (item["docstring"] == None or self.main_idea):
                class_name = item["name"]
                cls_structure = []
                cls_structure.append(class_name)
                cls_structure.append(item["attributes"])

                for method in item["methods"]:
                    cls_structure.append(
                        {
                            "method_name": method["method_name"],
                            "docstring": method["docstring"],
                        }
                    )
                cls_structure.append(item["docstring"])
                logger.info(
                    f"""{"Generating" if self.main_idea else "Updating"} docstring for the class: {item['name']} at {filename}"""
                )
                generated_cls_docstring = (
                    self.generate_class_documentation(cls_structure)
                    if self.main_idea is None
                    else self.update_class_documentation(cls_structure)
                )
                if not generated_cls_docstring:
                    logger.info(
                        f"Failed to recieve a proper docstring for the class {item['name']} at {filename}.\nRetrying ..."
                    )
                    generated_cls_docstring = (
                        self.generate_class_documentation(cls_structure)
                        if self.main_idea is None
                        else self.update_class_documentation(cls_structure)
                    )
                if generated_cls_docstring:
                    source_code = self.insert_cls_docstring_in_code(source_code, class_name, generated_cls_docstring)
                else:
                    logger.error(f"Could not recieve any response from the LLM.")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(source_code)
        logger.info(f"Updated file: {filename}")

    def generate_the_main_idea(self, parsed_structure: dict) -> None:
        prompt = (
            "You are an AI documentation assistant, and your task is to deduce the main idea of the project and formulate for which purpose it was written."
            "You are given with the list of the main components (classes and functions) with it's short description and location in project hierarchy:\n"
            "{components}\n\n"
            "Formulate only main idea without describing components. DO NOT list components, just return overview of the project and it's purpose."
            "Format you answer in a way you're writing markdown README file\n"
            "Use such format for result:\n"
            "# Name of the project\n"
            "## Overview\n"
            "## Purpose\n"
            "Keep in mind that your audience is document readers, so use a deterministic tone to generate precise content and don't let them know "
            "you're provided with any information. AVOID ANY SPECULATION and inaccurate descriptions! Now, provide the summarized idea of the project based on it's components"
        )
        structure = []
        for file in parsed_structure:
            for component in parsed_structure[file]["structure"]:
                t = component["type"]
                if t == "class":
                    docstring = component["docstring"].split("\n\n")[0].strip('"\n ') if component["docstring"] else ""
                else:
                    docstring = component["details"]["docstring"] if component["details"]["docstring"] else ""
                structure.append(
                    f"""{t.capitalize()} name: {component['name'] if t == "class" else component['details']['method_name']}
                Component description: {docstring}
                Component place in hierarchy: {file}
                Component importance score: {len(parsed_structure[file]['imports'])}
                """
                )
        logger.info(f"Generating the main idea of the project...")
        self.main_idea = self.model_handler.send_request(prompt.format(components="\n\n".join(structure)))

    def summarize_submodules(self, project_structure):
        summaries = {}
        self._rename_invalid_dirs(Path(self.config.git.name).resolve())

        def summarize_directory(name: str, file_summaries: List[str], submodule_summaries: List[str]) -> str:
            prompt = (
                "You are an AI documentation assistant, and your task is to sujmmarize the module of project and formulate for which purpose it was written."
                "You are given with the list of the components (classes and functions or submodules) with it's short description:\n\n"
                "{components}\n\n"
                "Also you have the snippet from README file of project from this module has came describing the main idea of the whole project:\n\n"
                "{main_idea}\n\n"
                "You should generate markdown-formatted documentation page describing this module using description of all files and all submodules.\n"
                "Do not too generalize overview and purpose parts using main idea, but try to explicit which part of main functionality does this module. Concentrate on local module features were infered previously.\n"
                "Format you answer in a way you're writing README file for the module. Use such template:\n\n"
                "# Name\n"
                "## Overview\n"
                "## Purpose\n"
                "Do not mention or describe any submodule or files! Rename snake_case names on meaningful names."
                "Keep in mind that your audience is document readers, so use a deterministic tone to generate precise content and don't let them know "
                "you're provided with any information. AVOID ANY SPECULATION and inaccurate descriptions! Now, provide the summarized idea of the module based on it's components"
            )

            components = [
                (
                    f"Module name: {name}",
                    "\n## Files Summary:\n\n- "
                    + "\n- ".join(file_summaries).replace("#", "##").replace("##", "###")
                    + "\n\n## Submodules Summary:\n"
                    + "\n- ".join(submodule_summaries).replace("#", "##"),
                )
            ]
            logger.info(f"Generating summary for the module {name}")
            result = self.model_handler.send_request(prompt.format(components=components, main_idea=self.main_idea))
            return result

        def traverse_and_summarize(path: Path, project_structure: Dict[str, Any]) -> str:
            dirs_summaries = []
            files_summaries = []

            dirs = [
                i
                for i in os.listdir(path)
                if os.path.isdir(Path(path, i)) and i not in [".git", ".github", "test", "tests"]
            ]
            files = [i for i in os.listdir(path) if not os.path.isdir(Path(path, i))]

            for dir_name in dirs:
                dir_path = Path(path, dir_name)
                dir_summary = traverse_and_summarize(dir_path, project_structure)
                if dir_summary:
                    dirs_summaries.append(dir_summary)

            for file_name in files:
                file_path = Path(path, file_name)
                if str(file_path) in project_structure:
                    files_summaries.append(
                        self.format_structure_openai_short(
                            filename=file_path.name, structure=project_structure[str(file_path)]
                        )
                    )
            if files_summaries or dirs_summaries:
                if path == self.config.git.name:  # main page of the repo
                    summary = self.main_idea

                else:
                    summary = summarize_directory(Path(path).name, files_summaries, dirs_summaries)
                summaries[str(path)] = summary
                return summary

        traverse_and_summarize(self.config.git.name, project_structure=project_structure)
        return summaries

    def convert_path_to_dot_notation(self, path):
        path_obj = Path(path) if isinstance(path, str) else path
        processed_parts = []
        for part in path_obj.parts:
            if part.endswith(".py"):
                part = part[:-3]
            if part == "__init__":
                continue
            processed_parts.append(part)
        dot_path = ".".join(processed_parts)
        return f"::: {dot_path}"

    def generate_documentation_mkdocs(self, path: str, files_info, modules_info) -> None:
        """
        Generates MkDocs documentation for a Python project based on provided path.

        Parameters:
            path: str - The path to the root directory of the Python project.

        Returns:
            None. The method generates MkDocs documentation for the project.
        """
        local = False
        repo_path = Path(path).resolve()
        mkdocs_dir = repo_path
        self._rename_invalid_dirs(repo_path)
        self._add_init_files(repo_path)

        init_doc_path = Path(repo_path, "osa_docs")
        init_doc_path.mkdir(parents=True, exist_ok=True)
        for file in files_info:
            if not files_info[file]["structure"]:
                continue
            parent_dir = Path(file).parent
            file_name = Path(file).name
            relative_path = Path(*Path(file).parts[1::])
            new_path = Path(init_doc_path, Path(*Path(parent_dir).parts[1::]))
            new_path.mkdir(parents=True, exist_ok=True)
            text = (
                f"# {file_name.strip('.py').replace('_', ' ').title()}\n\n"
                + "\n\n"
                + f"{self.convert_path_to_dot_notation(relative_path)}"
            )
            new_file = Path(new_path, file_name.replace(".py", ".md"))
            new_file.write_text(text)

        for module in modules_info:
            new_file = Path(init_doc_path, Path(*Path(module).parts[1::]))
            new_file.mkdir(parents=True, exist_ok=True)
            text = modules_info[module]
            Path(new_file, "index.md").write_text(text)

        mkdocs_config = osa_project_root().resolve() / "docs" / "templates" / "mkdocs.yml"
        mkdocs_yml = mkdocs_dir / "osa_mkdocs.yml"
        shutil.copy(mkdocs_config, mkdocs_yml)

        if local:
            result = subprocess.run(
                ["mkdocs", "build", "--config-file", str(mkdocs_yml)],
                check=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                logger.info(result.stdout)

            if result.stderr:
                logger.info(result.stderr)

            if result.returncode == 0:
                logger.info("MkDocs build completed successfully.")
            else:
                logger.error("MkDocs build failed.")
            shutil.rmtree(mkdocs_dir)
        logger.info(f"MKDocs configuration successfully built at: {mkdocs_dir}")

    def create_mkdocs_github_workflow(
        self,
        repository_url: str,
        path: str,
        filename: str = "osa_mkdocs",
        branches: list[str] = None,
    ) -> None:
        """
        Generates GitHub workflow .yaml for MkDocs documentation for a Python project.

        Parameters:
            repository_url: str - URI of the Python project's repository on GitHub.
            path: str - The path to the root directory of the Python project.
            filename: str - The name of the .yaml file that contains GitHub workflow for mkdocs deploying.
            branches: list[str] - List of branches to trigger the MkDocs workflow on

        Returns:
            None. The method generates GitHub workflow for MkDocs documentation of a current project.
        """
        clear_repo_name = re.sub(pattern="https://", repl="", string=repository_url)

        if not branches:
            branches = ["main", "master"]

        _workflow = {
            "name": "MkDocs workflow",
            "on": {
                "push": {"branches": branches},
                "pull_request": {"branches": branches},
            },
            "jobs": {
                "mkdocs_deployment": {
                    "name": "[OSA] Deploying MkDocs",
                    "runs-on": "ubuntu-latest",
                    "permissions": {"contents": "write"},
                    "steps": [
                        {
                            "name": "[OSA] Checking-out repository",
                            "uses": "actions/checkout@v4",
                        },
                        {
                            "name": "[OSA] Installing Python",
                            "uses": "actions/setup-python@v4",
                            "with": {"python-version": "3.12"},
                        },
                        {
                            "name": "[OSA] Installing MkDocs dependencies",
                            "run": "pip install mkdocs mkdocs-material mkdocstrings[python]",
                        },
                        {
                            "name": "[OSA] MkDocs documentation deploying",
                            "run": "mkdocs gh-deploy --force --config-file osa_mkdocs.yml",
                            "env": {"GITHUB_TOKEN": "${{ secrets.GITHUB_TOKEN }}"},
                        },
                    ],
                }
            },
        }

        workflows_path = f"{Path(path).resolve()}/.github/workflows"

        if not os.path.exists(workflows_path):
            os.makedirs(workflows_path)

        # Disable anchors use to run action
        yaml.Dumper.ignore_aliases = lambda self, data: True

        with open(f"{workflows_path}/{filename}.yml", mode="w") as actions:
            yaml.dump(data=_workflow, stream=actions, Dumper=yaml.Dumper, sort_keys=False)
        logger.info(
            f"In order to perform the documentation deployment automatically, please make sure that\n1. At {repository_url}/settings/actions following permission are enabled:\n\t1) 'Read and write permissions'\n\t2) 'Allow GitHub Actions to create and approve pull requests'\n2. 'gh-pages' branch is chosen as the source at 'Build and deployment' section at {repository_url}/settings/pages ."
        )

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """
        Sanitize a given name for use as an identifier.

        This method replaces any periods in the name with underscores
        and ensures that the name starts with an alphabetic character.
        If the name does not start with an alphabetic character, it
        prepends a 'v' to the name.

        Args:
            name: The name string to sanitize.

        Returns:
            The sanitized name as a string.
        """
        name = name.replace(".", "_")
        if not name[0].isalpha():
            name = "v" + name
        return name

    def _rename_invalid_dirs(self, repo_path: Path):
        """
        Renames directories within a specified path that have invalid names.

            This method recursively searches for directories within the given repository path,
            identifies those whose names are not valid Python identifiers or start with a dot,
            and renames them to valid names using a sanitization process. The method maintains a
            mapping of the original directory names to their new names.

            Args:
                repo_path: The path to the repository where directories will be checked and renamed.

            Returns:
                None.
        """

        all_dirs = sorted(
            [p for p in repo_path.rglob("*") if p.is_dir()],
            key=lambda p: len(p.parts),
            reverse=True,  # Rename from nested to parents'
        )

        for dir_path in all_dirs:
            if dir_path.name.startswith("."):
                continue
            if not dir_path.name.isidentifier():
                new_name = self._sanitize_name(dir_path.name)
                new_path = dir_path.parent / new_name

                if new_path.exists():
                    continue  # To avoid overwriting

                dir_path.rename(new_path)

    @staticmethod
    def _add_init_files(repo_path: Path):
        """
        Creates __init__.py files in all parent directories of Python files.

            This static method searches through the given repository path to find all
            Python files and adds an empty __init__.py file to each of their parent
            directories, excluding the directory containing the repository itself. This
            is useful for treating directories as Python packages.

            Args:
                repo_path: The path to the repository where the Python files are located.

            Returns:
                None
        """
        py_dirs = set()
        for py_file in repo_path.rglob("*.py"):
            if py_file.name != "__init__.py":
                parent = py_file.parent
                while parent != repo_path.parent:
                    py_dirs.add(parent)
                    if parent == repo_path:
                        break
                    parent = parent.parent

        for folder in py_dirs:
            init_path: Path = folder / "__init__.py"
            if not init_path.exists():
                init_path.touch()

    @staticmethod
    def _purge_temp_files(path: str):
        """
        Remove temporary files from the specified directory.

            This method deletes the 'mkdocs_temp' directory located within
            the given path if it exists. This is typically used to clean up
            temporary files if runtime error occured.

            Args:
                path: The path to the repository where the 'mkdocs_temp'
                        directory is located.

            Returns:
                None
        """
        repo_path = Path(path)
        mkdocs_dir = repo_path / "mkdocs_temp"
        if mkdocs_dir.exists():
            shutil.rmtree(mkdocs_dir)
