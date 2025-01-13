# Python Script Documentation

## High-Level Description
This Python script provides functionality for extracting the structure and details of a Python script. It includes classes and methods for processing the source code and generating documentation in a professional, detailed, and markdown-formatted manner.

## File: docgen.py

### Class: DocGen
- Method: **\_\_init\_\_**
  - Description: Initializes the class instance with the API key.
  - Args: ['self']
  - Return: None
  - Source:
    ```python
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY')
    ```

- Method: **generate_documentation_openai**
  - Description: Generates documentation using OpenAI's GPT-4 model based on the provided formatted structure.
  - Args: ['self', 'formatted_structure']
  - Return: None
  - Source:
    ```python
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


## File: osa_treesitter.py

### Class: OSA_TreeSitter
Class for the extraction of the source code's structure to be processed later by LLM.

Attributes:
- cwd: A current working directory with source code files.

- Method: **\_\_init\_\_**
  - Description: Initializes the class instance based on the provided path to the scripts.
  - Args: ['self', 'scripts_path']
  - Return: None
  - Source:
    ```python
    def __init__(self, scripts_path: str):
        self.cwd = scripts_path
    ```

- Method: **files_list**
  - Description: Provides a list of files occurring in the provided path along with status information.
  - Args: ['path']
  - Return: None
  - Source:
    ```python
    def files_list(path: str):
        # Implementation details
    ```

- Method: **_if_file_handler**
  - Description: Returns a path's head if a status trigger occurred.
  - Args: ['cls', 'path']
  - Return: None
  - Source:
    ```python
    def _if_file_handler(cls, path: str):
        # Implementation details
    ```

- Method: **open_file**
  - Description: Reads the content of the occurred file.
  - Args: ['path', 'file']
  - Return: str
  - Source:
    ```python
    def open_file(path: str, file: str) -> str:
        # Implementation details
    ```

- Method: **_parser_build**
  - Description: Builds the corresponding parser based on the file's extension.
  - Args: ['self', 'filename']
  - Return: Parser
  - Source:
    ```python
    def _parser_build(self, filename: str) -> Parser:
        # Implementation details
    ```

- Method: **_parse_source_code**
  - Description: Parses the provided file with the source code.
  - Args: ['self', 'filename']
  - Return: None
  - Source:
    ```python
    def _parse_source_code(self, filename: str):
        # Implementation details
    ```

- Method: **extract_structure**
  - Description: Extracts the structure of the occurred file in the provided directory.
  - Args: ['self', 'filename']
  - Return: list
  - Source:
    ```python
    def extract_structure(self, filename: str) -> list:
        # Implementation details
    ```

- Method: **_get_docstring**
  - Description: Retrieves class or method's docstring.
  - Args: ['self', 'block_node']
  - Return: str
  - Source:
    ```python
    def _get_docstring(self, block_node: tree_sitter.Node) -> str:
        # Implementation details
    ```

- Method: **_traverse_block**
  - Description: Traverses occurring in the file's tree structure "block" node.
  - Args: ['self', 'block_node', 'source_code']
  - Return: list
  - Source:
    ```python
    def _traverse_block(self, block_node: tree_sitter.Node, source_code: bytes) -> list:
        # Implementation details
    ```

- Method: **_extract_function_details**
  - Description: Extracts the details of "function_definition" node in the file's tree structure.
  - Args: ['self', 'function_node', 'source_code']
  - Return: dict
  - Source:
    ```python
    def _extract_function_details(self, function_node: tree_sitter.Node, source_code: str) -> dict:
        # Implementation details
    ```

- Method: **analyze_directory**
  - Description: Analyzes the provided directory.
  - Args: ['self', 'path']
  - Return: dict
  - Source:
    ```python
    def analyze_directory(self, path: str) -> dict:
        # Implementation details
    ```

- Method: **show_results**
  - Description: Prints out the results of the directory analysis.
  - Args: ['self', 'results']
  - Return: None
  - Source:
    ```python
    def show_results(self, results: dict):
        # Implementation details
    ```

- Method: **log_results**
  - Description: Logs the results of the directory analysis into "examples/report.txt".
  - Args: ['self', 'results']
  - Return: None
  - Source:
    ```python
    def log_results(self, results: dict):
        # Implementation details
    ```

---

This documentation provides a detailed overview of the Python script, including its classes, methods, and functionalities. Proper code formatting and structure are maintained to ensure clarity and readability.