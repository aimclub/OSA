import openai
import dotenv
import os
import re
import logging

from typing import Union

from OSA.osatreesitter.models import ModelHandlerFactory, ModelHandler
from readmeai.config.settings import ConfigLoader
from readmeai.readmegen_article.config.settings import ArticleConfigLoader

dotenv.load_dotenv()

import tiktoken


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

    def __init__(
            self,
            config_loader: Union[ConfigLoader, ArticleConfigLoader]):
        """
        Instantiates the object of the class.

        This method is a constructor that initializes the object by setting the 'api_key' attribute to the value of the 'OPENAI_API_KEY' environment variable.
        """
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(
            self.config)

    @staticmethod
    def format_structure_openai(structure: dict):
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
    def _format_class(item):
        """Formats class details."""
        class_str = f"  - Class: {item['name']}, line {item['start_line']}\n"
        if item["docstring"]:
            class_str += f"      Docstring: {item['docstring']}\n"
        for method in item["methods"]:
            class_str += DocGen._format_method(method)
        return class_str

    @staticmethod
    def _format_method(method):
        """Formats method details."""
        method_str = f"      - Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}\n"
        if method["docstring"]:
            method_str += f"          Docstring:\n        {method['docstring']}\n"
        method_str += f"        Source:\n{method['source_code']}\n"
        return method_str

    @staticmethod
    def _format_function(item):
        """Formats function details."""
        details = item["details"]
        function_str = f"  - Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}\n"
        if details["docstring"]:
            function_str += f"          Docstring:\n    {details['docstring']}\n"
        function_str += f"        Source:\n{details['source_code']}\n"
        return function_str

    @staticmethod
    def count_tokens(prompt, model="gpt-4"):
        """
        Counts the number of tokens in a given prompt using a specified model.

        Args:
            prompt: The text for which to count the tokens.
            model: The model to use for encoding. Defaults to "gpt-4".

        Returns:
            The number of tokens in the prompt.
        """
        enc = tiktoken.encoding_for_model(model)
        tokens = enc.encode(prompt)
        return len(tokens)

    def generate_class_documentation(self, class_details):
        """
        Generate documentation for a class.

        Args:
            class_details: A list of dictionaries containing method names and their docstrings.

        Returns:
            The generated class docstring.
        """
        # Construct a structured prompt
        prompt = f"""
        Generate a single Python docstring for the following class {class_details[0]['class_name']}. The docstring should follow Google-style format and include:
        - A short summary of what the class does.
        - A list of its methods.
        - A brief description of its methods.

        Class Methods:
        """
        for method in class_details:
            prompt += f"- {method['method_name']}: {method['docstring']}\n"

        return self.model_handler.send_request(prompt)

    def generate_method_documentation(self, method_details: dict):
        """
        Generate documentation for a single method.
        """
        prompt = f"""
        Generate a Python docstring for the following method. The docstring should follow Google-style format and include:
        - A short summary of what the method does.
        - A description of its parameters with types.
        - The return type and description.

        Method Details:
        - Method Name: {method_details["method_name"]}
        - Arguments: {method_details["arguments"]}
        - Return Type: {method_details["return_type"]}
        - Docstring: {method_details["docstring"]}
        - Source Code:
        ```
        {method_details["source_code"]}
        ```
        """
        return self.model_handler.send_request(prompt)

    def extract_pure_docstring(self, gpt_response: str):
        """
        Extracts only the docstring from the GPT-4 response while keeping triple quotes.

        Args:
            gpt_response: The full response from GPT-4.

        Returns:
            The properly formatted docstring including triple quotes.
        """
        # Regex to capture the full docstring with triple quotes
        match = re.search(r'("""+)\n?(.*?)\n?\1', gpt_response, re.DOTALL)

        if match:
            triple_quotes = match.group(
                1)  # Keep the triple quotes (""" or """)
            extracted_docstring = match.group(
                2
            )  # Extract only the content inside the docstring
            cleaned_content = re.sub(
                r"^\s*def\s+\w+\(.*?\):\s*", "", extracted_docstring,
                flags=re.MULTILINE
            )

            return f"{triple_quotes}\n{cleaned_content}{triple_quotes}"

        return '"""No valid docstring found."""'  # Return a placeholder if no docstring was found

    def insert_docstring_in_code(
            self, source_code, method_details, generated_docstring: str
    ):
        """
        This method inserts a generated docstring into the specified location in the source code.

        Args:
            source_code: The source code where the docstring should be inserted.
            method_details: A dictionary containing details about the method.
                It should have a key 'method_name' with the name of the method where the docstring should be inserted.
            generated_docstring: The docstring that should be inserted into the source code.

        Returns:
            None
        """
        # Matches a method definition with the given name,
        # including an optional return type. Ensures no docstring follows.
        method_pattern = rf"(def\s+{method_details['method_name']}\s*\([^)]*\)\s*(->\s*[a-zA-Z0-9_\[\], ]+)?\s*:\n)(\s*)(?!\s*\"\"\")"

        docstring_with_format = self.extract_pure_docstring(
            generated_docstring)
        updated_code = re.sub(
            method_pattern, rf"\1\3{docstring_with_format}\n\3", source_code,
            count=1
        )

        return updated_code

    def insert_cls_docstring_in_code(
            self, source_code, class_name, generated_docstring
    ):
        """
        Inserts a generated class docstring into the class definition.

        Args:
            source_code: The source code where the docstring should be inserted.
            class_details: A list of dictionaries containing method names and their docstrings.
            generated_docstring: The docstring that should be inserted.

        Returns:
            The updated source code with the class docstring inserted.
        """

        # Matches a class definition with the given name,
        # including optional parentheses. Ensures no docstring follows.
        class_pattern = (
            rf"(class\s+{class_name}\s*(\([^)]*\))?\s*:\n)(\s*)(?!\s*\"\"\")"
        )

        # Ensure we keep only the extracted docstring
        docstring_with_format = self.extract_pure_docstring(
            generated_docstring)

        updated_code = re.sub(
            class_pattern, rf"\1\3{docstring_with_format}\n\3", source_code,
            count=1
        )

        return updated_code

    def process_python_file(self, parsed_structure: dict):
        """
        Processes a Python file by generating and inserting missing docstrings.

        This method iterates over the given parsed structure of a Python codebase, checks each class method for missing
        docstrings, and generates and inserts them if missing. The method updates the source file with the new docstrings
        and prints the path of the updated file.

        Args:
            parsed_structure: A dictionary representing the parsed structure of the Python codebase.
                The dictionary keys are filenames and the values are lists of dictionaries representing
                classes and their methods.

        Returns:
            None
        """
        for filename, structure in parsed_structure.items():
            with open(filename, "r", encoding="utf-8") as f:
                source_code = f.read()
            for item in structure:
                if item["type"] == "class":
                    for method in item["methods"]:
                        if method[
                            "docstring"] == None:  # If docstring is missing
                            logging.info(
                                f"Generating docstring for method: {method['method_name']} in class {item['name']} at {filename}"
                            )
                            generated_docstring = self.generate_method_documentation(
                                method
                            )
                            if item["docstring"] == None:
                                method[
                                    "docstring"] = self.extract_pure_docstring(
                                    generated_docstring
                                )
                            source_code = self.insert_docstring_in_code(
                                source_code, method, generated_docstring
                            )

            for item in structure:
                if item["type"] == "class" and item["docstring"] == None:
                    class_name = item["name"]
                    cls_structure = []
                    for method in item["methods"]:
                        cls_structure.append(
                            {
                                "class_name": class_name,
                                "method_name": method["method_name"],
                                "docstring": method["docstring"],
                            }
                        )
                    logging.info(
                        f"Generating docstring for class: {item['name']} in class at {filename}"
                    )
                    generated_cls_docstring = self.generate_class_documentation(
                        cls_structure
                    )
                    source_code = self.insert_cls_docstring_in_code(
                        source_code, class_name, generated_cls_docstring
                    )
            with open(filename, "w", encoding="utf-8") as f:
                f.write(source_code)
            logging.info(f"Updated file: {filename}")

    def generate_method_documentation_md(self, method_details: dict):
        """
        Generate documentation for a single method using OpenAI GPT.
        """
        prompt = f"""
        Generate detailed documentation for the following Python method. Include:
        - Method name.
        - Arguments and their purposes.
        - Return type and its purpose.
        - A high-level explanation of what the method does.
        - Include the provided source code in the documentation.

        Method Details:
        - Method Name: {method_details["method_name"]}
        - Arguments: {method_details["arguments"]}
        - Return Type: {method_details["return_type"]}
        - Docstring: {method_details["docstring"]}
        - Source Code:
        ```
        {method_details["source_code"]}
        ```
        """

        return self.model_handler.send_request(prompt)

    def generate_documentation_openai(self, file_structure: dict,
                                      model="gpt-4"):
        """
        Generates the documentation for a given file structure using OpenAI's API.

        This method traverses the given file structure and for each class or standalone function, it generates
        its documentation. If the documentation is not available, it attempts to generate it using the OpenAI's API.
        The generated documentation is returned as a string.

        Args:
            self: The instance of the class where this method is defined.
            file_structure: A dictionary where keys are filenames and values are lists of dictionaries.
                Each dictionary represents a class or a standalone function in the file and contains information
                like its name, type (class or function), docstring, and methods (in case of a class).
            model: The model to be used by OpenAI's API to generate the documentation. Defaults to 'gpt-4'.

        Returns:
            The final documentation as a string.
        """
        final_documentation = ""

        for filename, structure in file_structure.items():
            final_documentation += self._format_file_header(filename)

            for item in structure:
                if item["type"] == "class":
                    final_documentation += self._format_class_doc(item, model)
                elif item["type"] == "function":
                    final_documentation += self._format_function_doc(item,
                                                                     model)

        return final_documentation

    def _format_file_header(self, filename):
        """Formats the header for a file in documentation."""
        return f"# Documentation for {filename}\n\n"

    def _format_class_doc(self, item, model):
        """Formats documentation for a class."""
        class_doc = f"## Class: {item['name']}\n\n{item['docstring'] or 'No docstring provided'}\n\n"
        for method in item["methods"]:
            class_doc += self._generate_method_doc(method, model)
        return class_doc

    def _format_function_doc(self, item, model):
        """Formats documentation for a standalone function."""
        function_details = item["details"]
        return self._generate_method_doc(function_details, model,
                                         is_function=True)

    def _generate_method_doc(self, method_details, model, is_function=False):
        """Generates documentation for a method or function."""
        doc_type = "Function" if is_function else "Method"
        try:
            logging.info(
                f"{doc_type} {method_details['method_name']}'s docstring is generating"
            )
            method_doc = self.generate_method_documentation_md(
                method_details=method_details
            )
            return (
                f"### {doc_type}: {method_details['method_name']}\n\n{method_doc}\n\n"
            )
        except Exception as e:
            logging.error(e, exc_info=True)
            return f"### {doc_type}: {method_details['method_name']}\n\nFailed to generate documentation.\n\n"
