import os
import re
import black
from pathlib import Path
import shutil
import subprocess

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
        prompt = f"""
        Generate a single Python docstring for the following class {class_details[0]}. The docstring should follow Google-style format and include:
        - A short summary of what the class does.
        - A list of its methods without details if class has them otherwise do not mention a list of methods.
        - A list of its attributes without types if class has them otherwise do not mention a list of attributes.
        - A brief summary of what its methods and attributes do if one has them for.
        """
        if len(class_details[1]) > 0:
            prompt += f"\nClass Attributes:\n"
            for attr in class_details[1]:
                prompt += f"- {attr}\n"

        if len(class_details[2:]) > 0:
            prompt += f"\nClass Methods:\n"
            for method in class_details[2:]:
                prompt += f"- {method['method_name']}: {method['docstring']}\n"

        return self.model_handler.send_request(prompt)

    def generate_method_documentation(self, method_details: dict, context_code: str = None) -> str:
        """
        Generate documentation for a single method.
        """
        prompt = f"""
        Generate a Python docstring for the following method. The docstring should follow Google-style format and include:
        - A short summary of what the method does.
        - A description of its parameters without types.
        - The return type and description.
        {"- Use provided source code of imported methods, functions to describe their usage." if context_code else ""}

        Method Details:
        - Method Name: {method_details["method_name"]}
        - Method decorators: {method_details["decorators"]}
        - Source Code:
        ```
        {method_details["source_code"]}
        ```
        {"- Imported methods source code:" if context_code else ""}
        {context_code if context_code else ""}
        """
        return self.model_handler.send_request(prompt)

    def extract_pure_docstring(self, gpt_response: str) -> str:
        """
        Extracts only the docstring from the GPT-4 response while keeping triple quotes.

        Args:
            gpt_response: The full response from GPT-4.

        Returns:
            The properly formatted docstring including triple quotes.
        """

        # Try to recover if closing triple-quote was replaced with ```
        triple_quote_pos = gpt_response.find('"""')
        if triple_quote_pos != -1:
            # Look for closing triple-quote
            closing_pos = gpt_response.find('"""', triple_quote_pos + 3)
            if closing_pos == -1:
                # Try to find a ``` after opening """
                broken_close_pos = gpt_response.find('```', triple_quote_pos + 3)
                if broken_close_pos != -1:
                    # Replace only this incorrect closing ``` with """
                    gpt_response = (
                        gpt_response[:broken_close_pos] + '"""' + gpt_response[broken_close_pos + 3:]
                    )

        # Regex to capture the full docstring with triple quotes
        match = re.search(r'("""+)\n?(.*?)\n?\1', gpt_response, re.DOTALL)

        if match:
            triple_quotes = match.group(1)  # Keep the triple quotes (""" or """)
            extracted_docstring = match.group(2)  # Extract only the content inside the docstring
            cleaned_content = re.sub(r"^\s*def\s+\w+\(.*?\):\s*", "", extracted_docstring, flags=re.MULTILINE)

            return f"{triple_quotes}\n{cleaned_content}{triple_quotes}"

        return '"""No valid docstring found."""'  # Return a placeholder if no docstring was found

    def insert_docstring_in_code(self, source_code: str, method_details: dict, generated_docstring: str) -> str:
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
        method_pattern = rf"((?:@\w+(?:\([^)]*\))?\s*\n)*\s*(?:async\s+)?def\s+{method_details['method_name']}\s*\((?:[^)(]|\((?:[^)(]*|\([^)(]*\))*\))*\)\s*(->\s*[a-zA-Z0-9_\[\],. |]+)?\s*:\n)(\s*)(?!\s*\"\"\")"
        """
        (
            (?:@\w+(?:\([^)]*\))?\s*\n)*                # Optional decorators: e.g. @decorator or @decorator(args), each followed by newline
            \s*                                         # Optional whitespace before function definition
            (?:async\s+)?                               # Optional 'async' keyword followed by whitespace
            def\s+{method_details['method_name']}\s*    # 'def' keyword followed by the specific method name and optional spaces
            \(                                          # Opening parenthesis for the parameter list
                (?:                                     # Non-capturing group to match parameters inside parentheses
                    [^)(]                               # Match any character except parentheses (simple parameter)
                    |                                   # OR
                    \(                                  # Opening a nested parenthesis
                        (?:[^)(]*|\([^)(]*\))*          # Recursively match nested parentheses content
                    \)                                  # Closing the nested parenthesis
                )*                                      # Repeat zero or more times (all parameters)
            \)                                          # Closing parenthesis of the parameter list
            \s*                                         # Optional whitespace after parameters
            (->\s*[a-zA-Z0-9_\[\],. |]+)?               # Optional return type annotation (e.g. -> int, -> dict[str, Any])
            \s*:\n                                      # Colon ending the function header followed by newline
        )
        (\s*)                                          # Capture indentation (spaces/tabs) of the next line (function body)
        (?!\s*\"\"\")                                  # Negative lookahead: ensure the next non-space characters are NOT triple quotes (no docstring yet)
        """

        docstring_with_format = self.extract_pure_docstring(generated_docstring)
        updated_code = re.sub(method_pattern, rf"\1\3{docstring_with_format}\n\3", source_code, count=1)

        return updated_code

    def insert_cls_docstring_in_code(self, source_code: str, class_name: str, generated_docstring: str) -> str:
        """
        Inserts a generated class docstring into the class definition.

        Args:

            source_code: The source code where the docstring should be inserted.
            class_name: Class name.
            generated_docstring: The docstring that should be inserted.

        Returns:
            The updated source code with the class docstring inserted.
        """

        # Matches a class definition with the given name,
        # including optional parentheses. Ensures no docstring follows.
        class_pattern = rf"(class\s+{class_name}\s*(\([^)]*\))?\s*:\n)(\s*)(?!\s*\"\"\")"

        # Ensure we keep only the extracted docstring
        docstring_with_format = self.extract_pure_docstring(generated_docstring)

        updated_code = re.sub(class_pattern, rf"\1\3{docstring_with_format}\n\3", source_code, count=1)

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
            self.format_with_black(filename)
            with open(filename, "r", encoding="utf-8") as f:
                source_code = f.read()
            for item in structure["structure"]:
                if item["type"] == "class":
                    for method in item["methods"]:
                        if method["docstring"] == None:  # If docstring is missing
                            logger.info(
                                f"Generating docstring for method: {method['method_name']} in class {item['name']} at {filename}"
                            )
                            method_context = self.context_extractor(method, parsed_structure)
                            generated_docstring = self.generate_method_documentation(method, method_context)
                            if item["docstring"] == None:
                                method["docstring"] = self.extract_pure_docstring(generated_docstring)
                            source_code = self.insert_docstring_in_code(source_code, method, generated_docstring)
                if item["type"] == "function":
                    func_details = item["details"]
                    if func_details["docstring"] == None:
                        logger.info(f"Generating docstring for a function: {func_details['method_name']} at {filename}")
                        generated_docstring = self.generate_method_documentation(func_details)
                        source_code = self.insert_docstring_in_code(source_code, func_details, generated_docstring)

            for item in structure["structure"]:
                if item["type"] == "class" and item["docstring"] == None:
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
                    logger.info(f"Generating docstring for class: {item['name']} in class at {filename}")
                    generated_cls_docstring = self.generate_class_documentation(cls_structure)
                    source_code = self.insert_cls_docstring_in_code(source_code, class_name, generated_cls_docstring)
            with open(filename, "w", encoding="utf-8") as f:
                f.write(source_code)
            self.format_with_black(filename)
            logger.info(f"Updated file: {filename}")

    def generate_documentation_mkdocs(self, path: str) -> None:
        """
        Generates MkDocs documentation for a Python project based on provided path.

        Parameters:
            path: str - The path to the root directory of the Python project.

        Returns:
            None. The method generates MkDocs documentation for the project.
        """
        local = False
        repo_path = Path(path).resolve()
        mkdocs_dir = repo_path / "mkdocs_temp"
        docs_output_path = repo_path / "site"

        if docs_output_path.exists() and local:
            shutil.rmtree(docs_output_path)
        if local:
            docs_output_path.mkdir()
        if mkdocs_dir.exists():
            shutil.rmtree(mkdocs_dir)
        mkdocs_dir.mkdir()

        self._rename_invalid_dirs(repo_path)

        docs_dir = mkdocs_dir / "docs"
        docs_dir.mkdir()

        self._add_init_files(repo_path)

        index_path = docs_dir / "index.md"
        index_content = "# Project Documentation\n\n"

        def is_valid_module_path(parts: tuple[str, ...]):
            return all(part.isidentifier() for part in parts)

        for py_file in repo_path.rglob("*.py"):
            rel_path = py_file.relative_to(repo_path)
            parts = rel_path.with_suffix("").parts
            if py_file.name == "__init__.py" or not is_valid_module_path(parts):
                continue
            module_path = ".".join(parts)
            index_content += f"## `{module_path}`\n\n::: {module_path}\n\n"

        index_path.write_text(index_content, encoding="utf-8")

        mkdocs_config = osa_project_root().resolve() / "docs" / "templates" / "mkdocs.yml"
        mkdocs_yml = mkdocs_dir / "mkdocs.yml"
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

    # It seems to better place it in the osa_tool/github_workflow
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
                    "steps": [
                        {
                            "name": "[OSA] Checking-out repository",
                            "uses": "actions/checkout@v4",
                        },
                        {
                            "name": "[OSA] Installing Python",
                            "uses": "actions/setup-python@v4",
                            "with": {"python-version": "3.10"},
                        },
                        {
                            "name": "[OSA] Installing MkDocs dependencies",
                            "run": "pip install mkdocs mkdocs-material mkdocstrings[python]",
                        },
                        {
                            "name": "[OSA] MkDocs documentation deploying",
                            "run": "mkdocs gh-deploy --force --config-file mkdocs_temp/mkdocs.yml",
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
