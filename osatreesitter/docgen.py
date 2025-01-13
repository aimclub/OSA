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

    def generate_documentation_openai(self, formatted_structure, model='gpt-3.5-turbo'):
        openai.api_key = self.api_key

        prompt = f"""
            I have extracted the structure and details of a Python script. Please generate professional, detailed, and markdown-formatted documentation for it. Use the provided structure to create the documentation.

            {formatted_structure}

            The documentation should include:
            - A high-level description of the script.
            - Documentation for each class, including its docstring and methods.
            - Documentation for each function, including its arguments, return type, and docstring.
            - Ensure proper formatting for headings, subheadings, code blocks, and lists.
                """

        prompt_size = self.count_tokens(prompt)
        print(f"Prompt size: {prompt_size} tokens")

        response = openai.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant for generating documentation.'},
                {'role': 'user', 'content': prompt},
            ],
            max_tokens = 4096,
            temperature=0.7,
        )

        return response.choices[0].message.content