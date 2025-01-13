import openai
import dotenv
import os

dotenv.load_dotenv()

class DocGen(object):
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')

    def generate_documentation_openai(self, formatted_structure, model='gpt-4'):
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

        response = openai.chat.completions.create(
            model=model,
            messages=[
                {'role': 'system', 'content': 'You are a helpful assistant for generating documentation.'},
                {'role': 'user', 'content': prompt},
            ],
            max_tokens=3000,
            temperature=0.7,
        )

        return response['choices'][0]['message']['content']