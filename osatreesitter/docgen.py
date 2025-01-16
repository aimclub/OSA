import openai
import dotenv
import os

dotenv.load_dotenv()

import tiktoken

class DocGen(object):
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')

    @staticmethod
    def format_structure_openai(structure: dict):
        formatted_structure = "The following is the structure of the Python files:\n\n"
        for filename, structures in structure.items():
            formatted_structure += f"File: {filename}\n"
            for item in structures:
                if item["type"] == "class":
                    formatted_structure += f"  - Class: {item['name']}, line {item['start_line']}\n"
                    if item["docstring"]:
                        formatted_structure += f"      Docstring: {item['docstring']}\n"
                    for method in item["methods"]:
                        formatted_structure += f"      - Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}\n"
                        if method["docstring"]:
                            formatted_structure += f"          Docstring:\n        {method['docstring']}\n"
                        formatted_structure += f"        Source:\n{method['source_code']}\n"
                elif item["type"] == "function":
                    details = item["details"]
                    formatted_structure += f"  - Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}\n"
                    if details["docstring"]:
                        formatted_structure += f"          Docstring:\n    {details['docstring']}\n"
                    formatted_structure += f"        Source:\n{details['source_code']}\n"
        return formatted_structure

    @staticmethod
    def count_tokens(prompt, model="gpt-4"):
        enc = tiktoken.encoding_for_model(model)
        tokens = enc.encode(prompt)
        return len(tokens)
    
    def generate_method_documentation(self, method_details: dict, model="gpt-4"):
        """
        Generate documentation for a single method using OpenAI GPT.
        """
        openai.api_key = self.api_key
        
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

        response = openai.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant for generating documentation."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
            temperature=0.7,
        )

        return response.choices[0].message.content

    def generate_documentation_openai(self, file_structure: dict, model="gpt-4"):
        """
        Generate comprehensive documentation for the given file structure.
        """
        final_documentation = ""

        for filename, structure in file_structure.items():
            final_documentation += f"# Documentation for {filename}\n\n"

            for item in structure:
                if item['type'] == 'class':
                    final_documentation += f"## Class: {item['name']}\n\n{item['docstring'] or 'No docstring provided'}\n\n"

                    for method in item['methods']:
                        try:
                            method_doc = self.generate_method_documentation(method_details=method, model=model)
                            final_documentation += f"### Method: {method['method_name']}\n\n{method_doc}\n\n"
                        except Exception as e:
                            final_documentation += f"### Method: {method['method_name']}\n\nError generating documentation: {e}\n\n"

                elif item['type'] == 'function':
                    final_documentation += "## Standalone Functions\n\n"
                    function_details = item['details']
                    try:
                        function_doc = self.generate_method_documentation(method_details=function_details, model=model)
                        final_documentation += f"### Function: {function_details['method_name']}\n\n{function_doc}\n\n"
                    except Exception as e:
                        final_documentation += f"### Function: {function_details['method_name']}\n\nError generating documentation: {e}\n\n"

        return final_documentation