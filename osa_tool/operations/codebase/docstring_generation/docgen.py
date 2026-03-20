import asyncio
import os
import re
import shutil
import subprocess
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import List, Dict, Callable

import aiofiles
import black
import black.report
import libcst as cst
import dotenv
import tiktoken
import tomli
import yaml

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandlerFactory, ProtollmHandler
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root
from osa_tool.operations.codebase.docstring_generation.osa_treesitter import OSA_TreeSitter
from osa_tool.operations.codebase.docstring_generation.topology import build_dependency_graph
from osa_tool.operations.codebase.docstring_generation.docstring_transformer import DocstringTransformer

dotenv.load_dotenv()


class DocGen(object):
    """
    The DocGen class facilitates automated generation and integration of Python docstrings using AI models. It handles the creation of documentation for classes and methods, structures Python file formatting, manages token counting for prompts, extracts docstrings from model responses, and inserts generated documentation into source code. Additionally, it processes entire Python files to identify and fill missing docstrings, enhancing code clarity and maintainability.
    
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


    def __init__(self, config_manager: ConfigManager):
        """
        Initializes a new DocGen instance.
        
        Args:
            config_manager: Configuration manager instance used to retrieve model settings for docstring generation.
        
        Why:
        - The method initializes the core components required for automated docstring generation.
        - It fetches the specific model configuration for the "docstrings" task from the configuration manager.
        - It builds a model handler based on those settings to interact with the underlying language model.
        - Internal state variables are set up to manage the generation process and cache function indices for efficiency.
        """
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("docstrings")
        self.model_handler: ProtollmHandler = ModelHandlerFactory.build(self.model_settings)
        self.main_idea = None
        self._function_index_cache = None

    @staticmethod
    def format_structure_openai(structure: dict) -> str:
        """
        Formats the structure of Python files in a readable string format.
        
        This method iterates over the given dictionary 'structure' and generates a formatted string where it describes each file, its classes and functions along with their details such as line number, arguments, return type, source code and docstrings if available. The formatting is delegated to helper methods for classes and functions to ensure consistent output. This structured representation is used by the OSA Tool to generate and maintain comprehensive repository documentation.
        
        Args:
            structure: A dictionary containing details of the Python files structure. The dictionary should have filenames as keys and values as lists of dictionaries. Each dictionary in the list represents a class or function and should contain keys like 'type', 'name', 'start_line', 'docstring', 'methods' (for classes), 'details' (for functions) etc. Each 'methods' or 'details' is also a dictionary that includes detailed information about the method or function.
        
        Returns:
            A formatted string representing the structure of the Python files, with each file's contents clearly delineated and each class or function formatted for readability.
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
        """
        Formats the structure of a Python file into a short, readable string.
        
        This method takes a file's structure information and produces a concise
        textual representation suitable for use with OpenAI models. It lists
        classes and functions found in the file.
        
        Args:
            filename: The name of the Python file whose structure is being formatted.
            structure: A dictionary containing the structural data of the file.
                It must contain a key "structure" which holds a list of items.
                Each item in the list is a dictionary with a "type" key (either "class" or "function")
                and other metadata used by helper methods to generate formatted summaries.
        
        Returns:
            A formatted string describing the file's structure. The string begins with a header,
            includes the filename, and then lists each class and function with a short summary
            (generated by internal helper methods). Returns an empty string if the structure list is empty.
        """
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
        """
        Formats class details into a structured string representation for documentation.
        
        This static method takes a dictionary containing class metadata and formats it into a human-readable string. It includes the class name, line number, docstring (if present), and recursively formats all methods belonging to the class using the helper method `_format_method`. This ensures consistent documentation sections for classes within the generated output.
        
        Args:
            item: A dictionary containing the following keys:
                - name: The name of the class.
                - start_line: The line number where the class starts in the source file.
                - docstring: The docstring of the class (may be empty or None).
                - methods: A list of dictionaries, each representing a method within the class.
        
        Returns:
            A formatted string representing the class details, suitable for inclusion in generated documentation.
        """
        class_str = f"  - Class: {item['name']}, line {item['start_line']}\n"
        if item["docstring"]:
            class_str += f"      Docstring: {item['docstring']}\n"
        for method in item["methods"]:
            class_str += DocGen._format_method(method)
        return class_str

    @staticmethod
    def _format_method(method: dict) -> str:
        """
        Formats method details into a structured string representation for documentation.
        
        This static method takes a dictionary containing method metadata and source code,
        and formats it into a human-readable string that includes the method name, arguments,
        return type, line number, docstring (if present), and the actual source code.
        It is used internally by the DocGen class to generate consistent documentation
        sections for methods.
        
        Args:
            method: A dictionary containing the following keys:
                - method_name: The name of the method.
                - arguments: The arguments of the method.
                - return_type: The return type of the method.
                - start_line: The line number where the method starts in the source file.
                - docstring: The docstring of the method (may be empty or None).
                - source_code: The full source code of the method.
        
        Returns:
            A formatted string representing the method details, suitable for inclusion
            in generated documentation.
        """
        method_str = f"      - Method: {method['method_name']}, Args: {method['arguments']}, Return: {method['return_type']}, line {method['start_line']}\n"
        if method["docstring"]:
            method_str += f"          Docstring:\n        {method['docstring']}\n"
        method_str += f"        Source:\n{method['source_code']}\n"
        return method_str

    @staticmethod
    def _format_function(item: dict) -> str:
        """
        Formats a function's details into a structured string for documentation.
        
        This method takes a dictionary containing parsed function metadata and formats it into a human-readable string. It is used to consistently present function information (like name, arguments, and source code) within generated documentation reports.
        
        Args:
            item: A dictionary containing the key 'details', which holds the function's metadata. Expected subkeys in 'details' include:
                - method_name: The name of the function.
                - arguments: The function's parameter list.
                - return_type: The function's return type annotation.
                - start_line: The line number in the source file where the function begins.
                - docstring: The function's docstring, if present.
                - source_code: The raw source code of the function.
        
        Returns:
            A formatted string representing the function. The output includes the function signature, line number, optional docstring, and its source code, each on separate lines with consistent indentation.
        """
        details = item["details"]
        function_str = f"  - Function: {details['method_name']}, Args: {details['arguments']}, Return: {details['return_type']}, line {details['start_line']}\n"
        if details["docstring"]:
            function_str += f"          Docstring:\n    {details['docstring']}\n"
        function_str += f"        Source:\n{details['source_code']}\n"
        return function_str

    @staticmethod
    def _format_class_short(item: dict) -> str:
        """
        Formats a class entry into a short, readable summary line.
        
        This method extracts the class name and the first paragraph of its docstring (if available)
        to produce a concise representation suitable for inclusion in a documentation summary.
        It is used internally to generate structured overviews of classes within the project.
        
        Args:
            item: A dictionary containing class information. Expected keys are 'name' for the class name
                  and 'docstring' for the raw docstring text.
        
        Returns:
            A formatted string representing the class. The string includes the class name on one line,
            and, if a docstring exists, its first paragraph (or the entire docstring if parsing fails)
            on the following line with indentation for readability.
        """
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
        """
        Formats a function's details into a short, readable string representation.
        
        This method extracts the function name and the first paragraph of its docstring (if available)
        to create a concise summary. It is used to generate brief, clean function listings in
        documentation outputs.
        
        Args:
            item: A dictionary containing a 'details' key, which itself holds the function's
                  metadata. The 'details' dictionary must include 'method_name' and may include
                  'docstring'.
        
        Returns:
            A formatted string representing the function. The format includes the function name
            and, if a docstring exists, its first paragraph (or the entire docstring if paragraph
            parsing fails). The output is intended for inclusion in larger documentation blocks.
        """
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
        Counts the number of tokens in a given prompt using the model specified in the class's model settings.
        
        This method is used to measure the length of a prompt in tokens, which is important for ensuring compatibility with model context windows and for managing usage costs.
        
        Args:
            prompt: The text for which to count the tokens.
        
        Returns:
            The number of tokens in the prompt.
        """
        enc = tiktoken.encoding_for_model(self.model_settings.model)
        tokens = enc.encode(prompt)
        return len(tokens)

    async def generate_class_documentation(self, class_details: list, semaphore: asyncio.Semaphore) -> str:
        """
        Generate documentation for a class by constructing a structured prompt and querying a language model.
        
        The method orchestrates the creation of a class-level docstring. It builds a detailed prompt from the provided class details, then uses an asynchronous model handler to generate the final docstring. A semaphore is used to limit concurrent requests to the model API, preventing overload and ensuring reliable operation.
        
        Args:
            class_details: A list where the first element is the class name, the second is a list of class attributes, and subsequent elements (except the last) are dictionaries for class methods. Each method dictionary contains 'method_name' and 'docstring' keys. The structure is used to build a comprehensive prompt.
            semaphore: An asyncio semaphore to limit the number of concurrent asynchronous requests to the model API, preventing rate limits or server overload.
        
        Returns:
            The generated class docstring as a string, with any surrounding triple quotes stripped.
        """
        # Construct a structured prompt
        prompt = (
            f"""Generate a single Python docstring for the following class {class_details[0]}. The docstring should follow Google-style format and include:\n"""
            "- A short summary of what the class does.\n"
            "- A list of its methods without details if class has them otherwise do not mention a list of methods.\n"
            "- A list of its attributes that explicitly mentioned at the constructor method's docstring (can be adressed as attributes, properties, class fields, etc.), without types if class or constructor method has them otherwise do not mention a list of attributes.\n"
            "- A brief summary of what its methods and attributes do if one has them for.\n\n"
            "Return only docstring without any quotation."
        )

        if len(class_details[1]) > 0:
            prompt += f"\nClass Attributes:\n"
            for attr in class_details[1]:
                prompt += f"- {attr}\n"

        if len(class_details[2:-1]) > 0:
            prompt += f"\nClass Methods:\n"
            for method in class_details[2:-1]:
                prompt += f"- {method['method_name']}: {method['docstring']}\n"

        async with semaphore:
            docstring = await self.model_handler.async_request(prompt)
            return docstring.strip('"""')

    async def update_class_documentation(self, class_details: list, semaphore: asyncio.Semaphore) -> str:
        """
        Generate documentation for a class by updating its existing description.
        
        This method takes an existing class docstring, splits it into a description and other content, and uses an AI model to refine the description based on the project's main idea. The semaphore controls concurrent API calls to prevent overloading.
        
        Args:
            class_details: A list where the last element is the full existing docstring. Earlier elements contain metadata (e.g., the class name at index 0). The docstring is expected to have a description followed by other sections separated by a double newline.
            semaphore: An asyncio semaphore to limit concurrent API requests, ensuring the service is not overwhelmed.
        
        Returns:
            The updated class docstring as a string. The description portion is rewritten by the AI model, while any other sections (like parameter lists or examples) are preserved unchanged.
        
        Why:
            The method updates only the descriptive part of a class docstring to better reflect the project context without altering technical details. This allows documentation to stay consistent with the project's purpose while preserving structured information.
        """
        # Construct a structured prompt
        try:
            desc, other = class_details[-1].split("\n\n", maxsplit=1)
            desc = desc.replace('"', "")
        except:
            return class_details[-1].strip().strip('"').strip("'")

        old_desc = desc.strip('"\n ')
        prompt = (
            f"""Update the provided description for the following Python class {class_details[0]} using provided main idea of the project.\n"""
            """Do not pay too much attention to the provided main idea - try not to mention it explicitly.\n"""
            f"""The main idea: {self.main_idea}\n"""
            f"""Old docstring description part: {old_desc}\n\n"""
            """Return only pure changed description - without any code, other parts of docs, any quotations)"""
        )

        async with semaphore:
            new_desc = await self.model_handler.async_request(prompt)
            new_desc = new_desc.strip().strip('"').strip("'")

        return "\n\n".join([new_desc, other])

    async def generate_method_documentation(
        self,
        method_details: dict,
        semaphore: asyncio.Semaphore,
        context_code: str = None,
    ) -> str:
        """
        Generate documentation for a single method by constructing a detailed prompt and querying an AI model.
        
        This method builds a structured prompt containing the method's source code, arguments, decorators, and optional context, then requests a docstring from an AI model. The prompt instructs the model to produce a Google‑style docstring with a summary, parameter descriptions, and, for constructors, a list of initialized class fields. The semaphore controls concurrent access to the model to prevent rate‑limiting.
        
        Args:
            method_details: A dictionary containing the method's name, source code, arguments, and decorators.
            semaphore: An asyncio semaphore to limit concurrent requests to the AI model.
            context_code: Optional documentation of related functions to provide context for the method.
        
        Returns:
            The generated docstring as a string, with surrounding triple quotes stripped.
        """
        arguments = [a for a in method_details["arguments"] if a not in ("self", "cls")]
        prompt = (
            "Generate a Python docstring for the following method. The docstring should follow Google-style format and include:\n"
            "- A short summary of what the method does.\n"
            "- A description of its parameters without types.\n"
            "- If the method is a class constructor, explicitly list all class fields (object properties) that are initialized, "
            "including their names and purposes. These fields should match the attributes assigned within the constructor "
            "(e.g., this.field = ..., self.field = ...). This information will be used to generate the class-level documentation.\n"
            "- The return type and description (omit Returns section if the method does not return a value).\n\n"
            f"- Method Name: {method_details['method_name']}\n\n"
            "Method source code: You are given only the body of a single method, without its signature. "
            "All visible code, including any inner functions or nested logic, belongs to this single method. "
            "Do NOT write separate docstrings for inner functions — they are part of the main method's logic.\n"
            "Do NOT repeat the function signature or decorators.\n"
            "```\n"
            f"{method_details['source_code']}\n"
            "```\n\n"
            "- List of arguments:\n"
            f"{arguments}\n\n"
            "Method Details:\n"
            f"- Method decorators: {method_details['decorators']}\n\n"
        )

        if context_code:
            prompt += (
                "Related functions documentation (for context only):\n"
                f"{context_code}\n\n"
                "Use this documentation ONLY to understand what the current method does.\n"
                "Do NOT document helper functions.\n"
                "Do NOT add their parameters to the Args section.\n"
                "Do NOT describe their internal implementation.\n\n"
            )

        prompt += (
            "Note:\n"
            "- DO NOT return the method body.\n"
            "- DO NOT invent parameters or behavior.\n"
            "- DO NOT count parameters which are not listed in the parameters list.\n"
            "- DO NOT lose any parameter.\n"
            "- DO NOT wrap any sections of the docstring into <any_tag> — remove such tags if generated.\n\n"
            "Return only the docstring without any quotation marks.\n"
        )

        async with semaphore:
            docstring = await self.model_handler.async_request(prompt)
            return docstring.strip('"""')

    async def update_method_documentation(
        self,
        method_details: dict,
        semaphore: asyncio.Semaphore,
        context_code: str = None,
        class_name: str = None,
    ) -> str:
        """
        Update documentation for a single method by generating an improved docstring via an AI model.
        
        This method constructs a detailed prompt based on the method's source code, existing docstring, and any provided context, then sends it to an AI model to produce an updated docstring. The semaphore controls concurrent requests to manage rate limits or resource usage.
        
        Args:
            method_details: A dictionary containing the method's name, source code, existing docstring, and decorators.
            semaphore: An asyncio semaphore to limit concurrent API calls.
            context_code: Optional source code of imported methods or helper functions to provide context for understanding the method's behavior.
            class_name: Optional name of the class containing the method, used to provide context in the prompt.
        
        Returns:
            The updated docstring as a string, with surrounding triple quotes stripped.
        """
        docstring = method_details["docstring"]

        prompt = (
            "Update the provided docstring for the following Python method.\n"
            "Preserve correct existing information and add missing details based on the source code.\n\n"
            "Guidelines:\n"
            "- Improve clarity and completeness without rewriting everything from scratch.\n"
            "- Answer WHY the method does what it does when it is not obvious.\n"
            "- If the original docstring contains only a description, add Args and Returns sections if needed.\n"
            "- Describe parameters without types.\n"
            "- Omit Returns section if the method does not return a value.\n"
            "- Do NOT invent parameters or behavior.\n\n"
            f"Original docstring:\n{docstring}\n\n"
            "Method Details:\n"
            f"- Method Name: {method_details['method_name']}"
            f"{f' (located inside {class_name} class)' if class_name else ''}\n"
            f"- Method decorators: {method_details['decorators']}\n\n"
            "Source Code:\n"
            "```\n"
            f"{method_details['source_code']}\n"
            "```\n\n"
        )

        if context_code:
            prompt += (
                "Imported methods / helper functions source code:\n"
                "```\n"
                f"{context_code}\n"
                "```\n\n"
                "Use this context ONLY to better understand the method behavior.\n"
                "Do NOT document helper functions.\n"
                "Do NOT mention their parameters explicitly.\n\n"
            )

        prompt += (
            f"The main idea of the project (for context only): {self.main_idea}\n\n"
            "Return only the updated docstring.\n"
            "DO NOT return code.\n"
            "Do NOT repeat the function signature or decorators.\n"
            "DO NOT return other documentation sections.\n"
            "Return only the docstring without any quotation marks.\n"
        )

        async with semaphore:
            docstring = await self.model_handler.async_request(prompt)
            return docstring.strip('"""')

    @staticmethod
    def extract_pure_docstring(gpt_response: str) -> str:
        """
        Extracts only the docstring from the GPT response while keeping triple quotes.
        Handles common formatting issues like Markdown blocks, extra indentation, and missing closing quotes.
        
        The method processes the LLM response through a series of fallback steps to isolate a clean docstring. This is necessary because LLM outputs can be inconsistent—they may include Markdown code blocks, partial or malformed triple quotes, or even leaked function definitions. The extraction prioritizes a properly quoted block if present, but will construct one if the response is sufficiently substantive.
        
        Args:
            gpt_response: Full response string from LLM.
        
        Returns:
            A properly formatted Python docstring string with triple quotes. If no valid content is extracted, returns a placeholder docstring: `
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
        Method to remove a docstring from the beginning of a method or function body.
        
        This is useful when extracting the actual executable code from a source string that may start with a docstring. It handles both single-line and multi-line docstrings.
        
        Args:
            body: The source code body of a method or function, potentially starting with a docstring.
        
        Returns:
            The body with any leading docstring removed. If no docstring is found at the start, the original body is returned unchanged.
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
            # Multiline docstring
            for i in range(1, len(lines)):
                if closing in lines[i]:
                    return "\n".join(lines[i + 1 :]).lstrip()
        return body

    @staticmethod
    def insert_docstring_in_code(
        source_code: str, method_details: dict, generated_docstring: str, class_method: bool = False
    ) -> str:
        """
        Inserts or replaces a method-level docstring in the provided source code,
        using the method's body from method_details['source_code'] to locate the method.
        Handles multi-line signatures, decorators, async definitions, and existing docstrings.
        
        Args:
            source_code: The full source code string where the docstring will be inserted or replaced.
            method_details: A dictionary containing at least a 'source_code' key with the exact method body (without its docstring) to locate the method.
            generated_docstring: The new docstring content to insert. It may contain surrounding quotes or be a raw string; it will be cleaned and formatted.
            class_method: If True, uses an 8‑space indent for the docstring; otherwise uses 4 spaces. This is needed because class methods are indented an extra level.
        
        Returns:
            The updated source code string with the docstring inserted or replaced. If the method body cannot be found in the source code, the original source code is returned unchanged.
        
        Why:
            This method ensures that generated docstrings are placed correctly within the source, respecting the existing structure and indentation. It locates the method by matching its body (stripped of any existing docstring) to avoid ambiguity from decorators or multi‑line signatures. The approach preserves surrounding whitespace and handles both single‑line and multi‑line docstring formatting.
        """
        method_body = DocGen.strip_docstring_from_body(method_details["source_code"].strip())
        docstring_clean = DocGen.extract_pure_docstring(generated_docstring)

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

                if len(method_lines[next_line_index].strip()) > 3 and method_lines[next_line_index].strip().endswith(
                    closing
                ):
                    method_lines = (
                        method_lines[:next_line_index] + [docstring_inserted] + method_lines[end_doc_idx + 1 :]
                    )
                    updated_block = "".join(method_lines)
                    result = source_code[:start] + updated_block + source_code[end:]
                    return result

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

    @staticmethod
    def insert_cls_docstring_in_code(source_code: str, class_name: str, generated_docstring: str) -> str:
        """
        Inserts or replaces a class-level docstring for a given class name.
        
        WHY: This method ensures that a class has a properly formatted and indented docstring, either by replacing an existing one or inserting a new one if missing. It is used to automatically update documentation generated by an LLM into the source code.
        
        Args:
            source_code: The full source code string.
            class_name: Name of the class to update.
            generated_docstring: The new docstring (raw response from LLM), which may contain extra formatting or quotes.
        
        Returns:
            Updated source code with the inserted or replaced class docstring. If the class is not found, the original source code is returned unchanged.
        
        Details:
            - The method uses a regex pattern to locate the class definition and any existing docstring.
            - It extracts a clean docstring from the LLM response via `DocGen.extract_pure_docstring`.
            - All lines of the new docstring are indented to match the class's indentation level.
            - If an existing docstring is present, it is replaced; otherwise, a new docstring is inserted after the class signature.
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

        docstring = DocGen.extract_pure_docstring(generated_docstring)

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

    def _build_function_index(self, parsed_structure: dict) -> dict:
        """
        Builds function index using OSA_TreeSitter's static method.
        Caches result to avoid rebuilding on every call.
        
        Args:
            parsed_structure: Complete parsed structure from analyze_directory()
        
        Returns:
            Dictionary mapping function names to their details
        
        Why:
            This method implements caching to improve performance when the function index is needed multiple times. Instead of rebuilding the index from the parsed structure on each call, it stores the result after the first build and returns the cached value thereafter.
        """
        if self._function_index_cache is None:
            self._function_index_cache = OSA_TreeSitter.build_function_index(parsed_structure)
        return self._function_index_cache

    def context_extractor(
        self,
        method_details: dict,
        structure: dict,
        function_index: dict = None,
        generated_docstrings: dict = None,
    ) -> str:
        """
        Extracts the context of function calls from given method_details using the 'method_calls' field.
        
        This method gathers documentation for functions called within a method to provide contextual understanding for documentation generation. It prioritizes using pre-generated docstrings (from a topological sort) if available, falling back to original docstrings from the function index.
        
        Args:
            method_details: A dictionary containing details about the method, including a 'method_calls' list of function names.
            structure: A dictionary representing the code structure, used for fallback search (though the current implementation primarily uses function_index).
            function_index: Optional index built by osa_treesitter.build_function_index() for fast O(1) lookup of function information. If not provided, the method returns an empty string.
            generated_docstrings: Optional dict mapping node_id to a generated docstring (from topological sort). Used to retrieve the most up-to-date documentation for called functions.
        
        Returns:
            A formatted string containing the context of called functions. If no called functions are found, the function index is missing, or no docstrings are available, an empty string is returned.
            The output format is:
            "Referenced helper functions (for context understanding only):\n"
            [For each function]
            "==========\n"
            "Helper function name: {display_name}\n"
            "Documentation:\n"
            "{docstring}\n"
            [End for each]
            "\nEnd of referenced helper functions\n"
        """

        called_functions = method_details.get("method_calls", [])

        if not called_functions:
            return ""

        if not function_index:
            return ""

        context = []

        for func_name in called_functions:
            search_name = func_name.split(".")[-1] if "." in func_name else func_name

            if search_name in function_index:
                func_info = function_index[search_name]
                class_name = func_info.get("class", "")
                display_name = f"{class_name}.{search_name}" if class_name else search_name

                # Use generated docstring if available (from topological sort)
                docstring = None
                if generated_docstrings:
                    # Try to find in generated_docstrings by node_id
                    file_path = func_info.get("file", "")
                    if class_name:
                        node_id = f"{file_path}:{class_name}.{search_name}"
                    else:
                        node_id = f"{file_path}:{search_name}"

                    docstring = generated_docstrings.get(node_id)

                # Fallback to original docstring
                if not docstring:
                    docstring = func_info.get("docstring")

                if not docstring:
                    continue

                separator = "=" * 10
                instance_prompt = (
                    separator + "\n" f"Helper function name: {display_name}\n" f"Documentation:\n{docstring}\n"
                )

                context.append(instance_prompt)

        if not context:
            return ""

        return (
            "Referenced helper functions (for context understanding only):\n"
            + "\n".join(context)
            + "\nEnd of referenced helper functions\n"
        )

    @staticmethod
    def format_with_black(filename):
        """
        Formats a Python source code file using the `black` code formatter.
        
        This method takes a filename as input and formats the code in the specified file using the `black` code formatter. It is used to ensure consistent code style and readability across the project's Python files.
        
        Args:
            filename: The path to the Python source code file to be formatted.
        
        Returns:
            None
        
        Note:
            The formatting is performed in-place with `black`'s default settings, using fast mode for performance and writing changes directly back to the file.
        """
        black.format_file_in_place(
            Path(filename),
            fast=True,
            mode=black.FileMode(),
            write_back=black.WriteBack.YES,
        )

    @staticmethod
    def _run_in_executor(
        parsed_structure: dict, project_source_code: dict, generated_docstrings: dict, n_workers: int = 8
    ) -> list[dict]:
        """
        Runs docstrings insertion tasks in multiprocessing mode.
        For correct execution, all objects that would be sent to the processes must be pickle-able.
        The results will be received in the order in which they were sent to the executor.
        
        Args:
            parsed_structure: Parsed structure of the current project containing all files and their metadata.
            project_source_code: Serialized version of the source code.
            generated_docstrings: Docstrings to be inserted into the source code.
            n_workers: The number of worker processes to use for CPU-bound tasks. Defaults to 8.
        
        Returns:
            list[dict]: A list of dictionaries, each representing the result of a docstring insertion task for a file.
            The order of results matches the order of files processed.
        
        Why:
            This method uses multiprocessing to parallelize the insertion of docstrings into multiple source files,
            which is a CPU-intensive operation. It filters the parsed structure to include only files that have a
            "structure" entry, maps the necessary arguments for each file, and distributes the work across a
            ProcessPoolExecutor to improve performance on multi-core systems.
        """

        structure = [k for k, v in parsed_structure.items() if v.get("structure")]

        # mapping the arguments for cpu-bound tasks
        args = [(file, project_source_code[file], generated_docstrings[file]) for file in structure]

        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            result = list(executor.map(DocGen._perform_code_augmentations, args))

        return result

    @staticmethod
    def _perform_code_augmentations(args) -> dict[str, str]:
        """
        Performs the insertion of generated docstrings into the provided source code.
        This method contains the main CPU-bound work of the current "docstrings" algorithm due to regex usage in the underlying DocGen insertion methods.
        
        Args:
            args: A tuple containing three elements: the filename, its source code as a string, and a collection of generated docstrings to be inserted.
        
        Returns:
            dict[str, str]: A dictionary mapping the input filename to the augmented source code string after docstring insertion. If no docstrings are provided, the original source code is returned unchanged under the same filename.
        
        Why:
            This method is static to allow parallel execution, as the docstring insertion for each file is independent and CPU-intensive. It uses the LibCST library to parse and transform the source code, ensuring that docstrings are inserted at the correct locations while preserving the original code structure and formatting.
        """

        # unpack the given arguments
        file, source_code, docstrings = args

        logger.info(f"Augmenting code for the file: {file}")

        if not docstrings:
            return {file: source_code}

        module = cst.parse_module(source_code)
        wrapper = cst.MetadataWrapper(module)
        transformer = DocstringTransformer(docstrings, source_code.splitlines(True), module.default_indent)
        new_module = wrapper.visit(transformer)

        # serialize the results to a dictionary
        return {file: new_module.code}

    async def _generate_docstrings_for_items(
        self, parsed_structure: dict, docstring_type: tuple | str, rate_limit: int = 10
    ) -> dict[str, dict]:
        """
        Generates docstrings for all structures in the given project by interacting with an LLM.
        
                Args:
                    parsed_structure: Parsed structure of the current project containing all files and their metadata.
                    docstring_type: Defines the docstring generation strategy. Valid values are:
                        - ('functions', 'methods'): Generate docstrings only for functions and methods.
                        - 'classes': Generate docstrings only for classes.
                        - ('functions', 'methods', 'classes'): Generate docstrings for all three structure types.
                    rate_limit: Maximum number of concurrent API requests to the LLM server. Defaults to 10.
        
                Returns:
                    A dictionary where keys are filenames and values are dictionaries containing the generated docstrings
                    for the structures in that file.
        
                Note:
                    The method uses different internal handlers based on the docstring_type:
                    - For ('functions', 'methods') or ('functions', 'methods', 'classes'), it calls _fetch_docstrings.
                    - For 'classes', it iterates through parsed_structure to count classes needing docstrings and calls
                      _fetch_docstrings_for_class with progress tracking.
                    Files without any functions, methods, or classes are skipped, and a log message is issued.
                    An invalid docstring_type raises a ValueError.
        """

        semaphore = asyncio.Semaphore(rate_limit)

        async def _iterate_and_collect(project_structure: dict, collect_fn: Callable, *args) -> dict[str, dict]:
            """Iterates over project structure and generates the docstrings by given callable"""
            results = {}

            for filename, structure in project_structure.items():
                # if structure contains empty file, there are no purpose for docstrings generation.
                if structure.get("structure"):
                    results[filename] = await collect_fn(filename, structure, *args)
                else:
                    logger.info(f"File {filename} does not contain any functions, methods or class constructions.")
            return results

        logger.info(f"Docstrings {'update' if self.main_idea else 'generation'} for the project has started!")

        match docstring_type:
            case ("functions", "methods") | ("functions", "methods", "classes"):
                generating_results = await self._fetch_docstrings(
                    parsed_structure, docstring_type, semaphore, rate_limit
                )
            case "classes":
                total_classes = sum(
                    1
                    for file_meta in parsed_structure.values()
                    for item in (file_meta.get("structure") if isinstance(file_meta.get("structure"), list) else [])
                    if item.get("type") == "class" and (not item.get("docstring") or self.main_idea)
                )
                class_progress = {"count": 0, "total": total_classes}
                generating_results = await _iterate_and_collect(
                    parsed_structure, self._fetch_docstrings_for_class, semaphore, class_progress
                )

            case _:
                raise ValueError(
                    "Invalid docstrings_type passed! It must be ('functions', 'methods') or 'classes' or ('functions', 'methods', 'classes')"
                )

        logger.info(f"Docstrings generation for the project is complete!")
        return generating_results

    @staticmethod
    async def _get_project_source_code(parsed_structure: dict, sem: asyncio.Semaphore) -> dict[str, str]:
        """
        Concurrently reads each file of a given project and serializes source code into a pickle-able object for future use in multiprocessing CPU-bound tasks.
        
        Args:
            parsed_structure: Parsed structure of the current project containing all files and their metadata. Only items where the "structure" key has a truthy value are processed as readable files.
            sem: Asynchronous semaphore to limit concurrent file I/O operations, preventing system overload and managing resource usage.
        
        Returns:
            A dictionary mapping each file path (str) to its corresponding source code content (str). Only files with a defined "structure" in parsed_structure are included.
        
        Why:
            This method enables efficient, non-blocking file reading across many files by using asyncio and a semaphore for controlled concurrency. The resulting dictionary is pickle-able, allowing it to be easily passed to separate processes for CPU-intensive documentation generation or analysis tasks without repeated I/O overhead.
        """

        structure = [k for k, v in parsed_structure.items() if v.get("structure")]

        # single file reading coroutine
        async def _read_code(file: str) -> tuple:
            async with sem:
                async with aiofiles.open(file, mode="r", encoding="utf-8") as f:
                    return file, await f.read()

        # collecting the results, then serializing
        result = await asyncio.gather(*[_read_code(file) for file in structure])

        return {file: code for file, code in result}

    @staticmethod
    async def _write_augmented_code(parsed_structure: dict, augmented_code: list[dict], sem: asyncio.Semaphore) -> None:
        """
        Writes given code after docstrings insertion in necessary files concurrently.
        
        This method writes the augmented code (with inserted docstrings) back to the corresponding files in the project structure. It processes only files that have a "structure" entry in the parsed metadata, ensuring that only relevant, parsed files are updated. The writes are performed concurrently with a semaphore to limit simultaneous file‑system operations and prevent overload.
        
        Args:
            parsed_structure: Parsed structure of the current project containing all files and their metadata.
            augmented_code: List of code snippets, each a dictionary mapping file paths to the augmented code with inserted docstrings.
            sem: Semaphore used to control concurrent access to the file‑system, preventing excessive simultaneous writes.
        
        Returns:
            None
        """

        structure = [k for k, v in parsed_structure.items() if v.get("structure")]

        # single file writing coroutine
        async def _write_code(file: str, code: str) -> None:
            async with sem:
                async with aiofiles.open(file, mode="w", encoding="utf-8") as f:
                    await f.write(code)

        # executing coroutines concurrently
        await asyncio.gather(*[_write_code(f, augmented_code[i][f]) for i, f in enumerate(structure)])

    async def _generate_node(
        self,
        node_id: str,
        dep_graph,
        parsed_structure: dict,
        function_index: dict,
        generated_docstrings: dict,
        semaphore: asyncio.Semaphore,
        docstring_type: tuple | str,
        progress: dict,
    ):
        """
        Generate a docstring for a single node (function or method) using context from its completed dependencies.
        
        This method processes one node from the dependency graph, checking if it should be documented based on the node type and configuration. It then gathers relevant context from already documented dependencies and either generates a new docstring or updates an existing one, depending on the tool's mode.
        
        Args:
            node_id: The unique identifier of the node in the dependency graph.
            dep_graph: The dependency graph containing node metadata and relationships.
            parsed_structure: The parsed abstract syntax tree (AST) structure of the source code.
            function_index: A mapping of function/method names to their metadata for quick lookup.
            generated_docstrings: A dictionary of already generated docstrings for other nodes, used to provide context.
            semaphore: An asyncio semaphore to limit concurrent API requests or processing.
            docstring_type: A tuple or string specifying which types of nodes (e.g., functions, methods, classes) should be documented.
            progress: A dictionary tracking progress, containing 'count' and 'total' keys for logging.
        
        Returns:
            A tuple containing (node_id, node_type, file_path, generated_docstring, metadata) if a docstring is successfully generated or updated; otherwise, None. Returns None if the node is not found, already has a docstring (in generation mode), or is filtered out by docstring_type.
        
        Why:
            The method ensures documentation is generated in dependency order, providing necessary context from already documented items. It filters nodes based on type and configuration to avoid unnecessary processing and respects rate limits via the semaphore. In 'main_idea' (update) mode, it updates existing docstrings; otherwise, it generates new ones.
        """
        node_info = dep_graph.get_node_metadata(node_id)
        if not node_info:
            return None

        node_type = node_info["type"]
        metadata = node_info["metadata"]
        file_path = node_info["file"]

        if metadata.get("docstring") and not self.main_idea:
            logger.debug(f"Skipping {node_id}: already has docstring")
            return None

        if node_type == "method" and docstring_type not in [
            ("functions", "methods"),
            ("functions", "methods", "classes"),
        ]:
            return None
        if node_type == "function" and docstring_type not in [
            ("functions", "methods"),
            ("functions", "methods", "classes"),
        ]:
            return None

        progress["count"] += 1
        progress_label = f"[{progress['count']}/{progress['total']}]"

        if node_type == "method":
            logger.info(
                f"""{progress_label} Requesting for docstrings {"update" if self.main_idea else "generation"} for the method: {metadata["method_name"]} of class {node_info.get("class", "")} at {file_path}"""
            )
        elif node_type == "function":
            logger.info(
                f"""{progress_label} Requesting for docstrings {"update" if self.main_idea else "generation"} for the function: {metadata["method_name"]} at {file_path}"""
            )

        context = self.context_extractor(metadata, parsed_structure, function_index, generated_docstrings)

        try:
            if self.main_idea:
                if node_type == "method":
                    class_name = node_info.get("class", "")
                    docstring = await self.update_method_documentation(metadata, semaphore, context, class_name)
                else:
                    docstring = await self.update_method_documentation(metadata, semaphore, context)
            else:
                docstring = await self.generate_method_documentation(metadata, semaphore, context)

            return (node_id, node_type, file_path, docstring, metadata) if docstring else None

        except Exception as e:
            logger.error(f"Error generating docstring for {node_id}: {e}")
            return None

    async def _fetch_docstrings(
        self,
        parsed_structure: dict,
        docstring_type: tuple | str,
        semaphore: asyncio.Semaphore,
        rate_limit: int,
    ) -> dict[str, dict]:
        """
        Generates docstrings for functions and methods using dependency-first processing.
        
        Builds a dependency graph from the parsed structure, then generates docstrings in topological order while propagating context from already generated docstrings. This ensures that dependencies are documented before dependents, allowing context (like parameter types or return values inferred from dependencies) to inform the generation of dependent docstrings. Optionally adds class docstrings when docstring_type includes "classes".
        
        Args:
            parsed_structure: Parsed structure of the current project containing all files and their metadata.
            docstring_type: Defines the docstring generation strategy. Can be a string or tuple specifying which types (e.g., "functions", "methods", "classes") to generate.
            semaphore: Asynchronous semaphore to limit concurrent requests, preventing overload on the external LLM server API.
            rate_limit: Maximum number of concurrent generation tasks allowed at once, controlling the rate of requests to the LLM.
        
        Returns:
            dict[str, dict]: A dictionary mapping each file path to a dict with keys "methods", "functions", and "classes". Each key holds a list of tuples, where each tuple contains the generated docstring and its associated metadata for the corresponding node in that file.
        """
        logger.info("Using topological sorting with context propagation for dependency-first generation")
        logger.info("Building dependency graph for topological sort...")

        # Build dependency graph
        dep_graph = build_dependency_graph(parsed_structure)

        # Build function index for context extraction
        function_index = self._build_function_index(parsed_structure)

        # Storage for generated docstrings (node_id -> docstring)
        generated_docstrings = {}

        # Storage for results in original format: {file: {"methods": [...], "functions": [...], "classes": [...]}}
        results = {file: {"methods": [], "functions": [], "classes": []} for file in parsed_structure.keys()}
        total_nodes = len(dep_graph.nodes)
        progress = {"count": 0, "total": total_nodes}

        in_degree = {node: len(dep_graph.get_dependencies(node)) for node in dep_graph.nodes}
        queue = [node for node, degree in in_degree.items() if degree == 0]

        in_progress = {}
        completed = set()

        logger.info(f"Starting eager topological processing: {len(queue)} nodes ready, {total_nodes} total")

        while queue or in_progress:
            while queue and len(in_progress) < rate_limit:
                node_id = queue.pop(0)
                task = asyncio.create_task(
                    self._generate_node(
                        node_id,
                        dep_graph,
                        parsed_structure,
                        function_index,
                        generated_docstrings,
                        semaphore,
                        docstring_type,
                        progress,
                    )
                )
                in_progress[node_id] = task

            if not in_progress:
                break

            done, _ = await asyncio.wait(in_progress.values(), return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                completed_node_id = None
                for node_id, t in in_progress.items():
                    if t == task:
                        completed_node_id = node_id
                        break

                if completed_node_id is None:
                    continue

                del in_progress[completed_node_id]
                completed.add(completed_node_id)

                try:
                    result = await task

                    if result and not isinstance(result, Exception):
                        node_id, node_type, file_path, docstring, metadata = result

                        generated_docstrings[node_id] = docstring

                        if node_type == "method":
                            results[file_path]["methods"].append((docstring, metadata))
                        elif node_type == "function":
                            results[file_path]["functions"].append((docstring, metadata))

                except Exception as e:
                    logger.error(f"Task failed for {completed_node_id}: {e}")

                for dependent_id in dep_graph.reverse_graph.get(completed_node_id, set()):
                    deps = dep_graph.get_dependencies(dependent_id)
                    if all(dep in completed for dep in deps):
                        if (
                            dependent_id not in queue
                            and dependent_id not in in_progress
                            and dependent_id not in completed
                        ):
                            queue.append(dependent_id)

        if docstring_type == ("functions", "methods", "classes"):
            total_classes = sum(
                1
                for file_meta in parsed_structure.values()
                for item in (file_meta.get("structure") if isinstance(file_meta.get("structure"), list) else [])
                if item.get("type") == "class" and (not item.get("docstring") or self.main_idea)
            )
            logger.info(f"Generating class docstrings... Total classes: {total_classes}")
            class_progress = {"count": 0, "total": total_classes}
            class_results = {}

            for file_path, file_meta in parsed_structure.items():
                if not file_meta.get("structure"):
                    continue

                class_results[file_path] = await self._fetch_docstrings_for_class(
                    file_path, file_meta, semaphore, class_progress
                )

            for file_path in results.keys():
                if file_path in class_results:
                    results[file_path]["classes"] = class_results[file_path].get("classes", [])

        return results

    async def _fetch_docstrings_for_class(
        self,
        file: str,
        file_meta: dict,
        semaphore: asyncio.Semaphore,
        progress: dict,
    ) -> dict[str, list]:
        """
        Collects a batch of requests for each class in a given file based on its metadata, then concurrently executes the requests and returns the results in a structured dictionary.
        
        For each class in the file metadata that either lacks a docstring or when `self.main_idea` is True, a request coroutine is created to generate or update the class documentation. The method uses a semaphore to limit concurrent requests and avoid overloading the external LLM‑server API. Progress is tracked and logged during the operation.
        
        Args:
            file: The name of the file being processed.
            file_meta: Dictionary containing metadata about the file, including its structure (list of classes, methods, etc.).
            semaphore: Asynchronous semaphore used to throttle concurrent API requests.
            progress: Dictionary tracking progress across classes, formatted as {"count": int, "total": int}. The "count" is incremented for each class processed.
        
        Returns:
            A dictionary with a single key "classes", whose value is a list of tuples. Each tuple contains (docstring_result, class_name) for every class that received a non‑empty docstring result. Classes that yield an empty result are filtered out.
        """

        _coroutines = []

        for item in file_meta["structure"]:

            _type = item["type"]

            match _type:
                case "class":

                    if not item.get("docstring") or self.main_idea:

                        # collecting a class metadata ahead
                        class_name = item["name"]
                        class_metadata = [class_name, item["attributes"]]

                        # enrich the class metadata by meta about it's methods
                        for method in item["methods"]:

                            class_metadata.append(
                                {"method_name": method["method_name"], "docstring": method["docstring"]}
                            )

                        class_metadata.append(item["docstring"])

                        progress["count"] += 1
                        progress_label = f"[{progress['count']}/{progress['total']}]"

                        logger.info(
                            f"""{progress_label} Requesting for docstrings {"update" if self.main_idea else "generation"} for the class: {item["name"]} at {file}"""
                        )

                        request_coroutine = (
                            self.generate_class_documentation(class_metadata, semaphore)
                            if not self.main_idea
                            else self.update_class_documentation(class_metadata, semaphore)
                        )

                        # just add new coroutine and class name to a task list
                        _coroutines.append((class_name, request_coroutine))

        fetched_docstrings = await asyncio.gather(*[task[1] for task in _coroutines])
        structure_names = [name[0] for name in _coroutines]

        return {"classes": [pair for pair in zip(fetched_docstrings, structure_names) if pair[0]]}

    async def generate_the_main_idea(self, parsed_structure: dict, top_n: int = 5) -> None:
        """
        Generates the main idea of the project based on its key components.
                
                This method analyzes the parsed project structure to identify the most important
                components (based on import counts), constructs a prompt for an AI model, and
                asynchronously requests the model to generate a concise project overview and
                purpose statement. The result is stored as an instance attribute.
                
                Why: The method uses import counts as a heuristic for component importance because
                frequently imported components often represent core functionality or central modules
                in a project. This focuses the AI model on the most relevant parts when generating
                the project overview.
                
                Args:
                    parsed_structure: A dictionary representing the parsed structure of the
                        project, containing file paths as keys and their component details.
                        Each value should contain 'imports' and 'structure' keys.
                    top_n: The number of top components (by import count) to consider when
                        generating the main idea. Defaults to 5.
                
                Initializes the following class fields (object properties):
                    main_idea: The generated project overview and purpose statement as returned
                        by the AI model. The output is formatted as markdown with '# Name of the project',
                        '## Overview', and '## Purpose' sections.
                
                Note:
                    - Excludes files containing '.git', '.github', 'test', 'tests', '__init__', or '__pycache__'.
                    - For classes, uses the first paragraph of the docstring; for functions, uses the full docstring.
                    - The prompt instructs the AI model to avoid speculation, list components, or reveal its source information.
        """

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

        _exclusions = (".git", ".github", "test", "tests", "__init__", "__pycache__")

        prompt_structure = []

        accepted_packages = [
            (str(f), len(parsed_structure[f]["imports"]))
            for f in parsed_structure
            if all(e not in f for e in _exclusions)
        ]

        importance_top = sorted(accepted_packages, key=lambda pair: pair[1], reverse=True)[:top_n]

        for file, score in importance_top:

            for component in parsed_structure[file]["structure"]:

                _type = component["type"]

                if _type == "class":
                    docstring = component["docstring"].split("\n\n")[0].strip('"\n ') if component["docstring"] else ""
                else:
                    docstring = component["details"]["docstring"] if component["details"]["docstring"] else ""

                prompt_structure.append(f"""
                    {_type.capitalize()} name: {component["name"] if _type == "class" else component["details"]["method_name"]}
                    Component description: {docstring}
                    Component place in hierarchy: {file}
                    Component importance score: {score}
                    """)

        logger.info(f"Generating the main idea of the project...")

        components = "\n\n".join(prompt_structure)

        self.main_idea = await self.model_handler.async_request(prompt.format(components=components))

    async def summarize_submodules(self, project_structure, rate_limit: int = 20) -> Dict[str, str]:
        """
        This method performs recursive traversal over given parsed structure of a Python codebase and
        generates short summaries for each directory (submodule).
        
        Args:
            project_structure: A dictionary representing the parsed structure of the Python codebase.
                The dictionary keys are filenames and the values are lists of dictionaries representing
                classes and their methods.
            rate_limit: The maximum number of concurrent requests allowed to the LLM API.
        
        Returns:
            A dictionary mapping directory paths (as strings) to their generated markdown summaries.
        
        Why:
            The method recursively traverses the project directory, excluding certain folders (like .git, tests),
            and uses an LLM to generate a structured markdown summary for each submodule. This creates
            hierarchical documentation that reflects the project's organization, linking each module's purpose
            to the overall project idea.
        """

        self._rename_invalid_dirs(Path(self.config_manager.get_git_settings().name).resolve())

        semaphore = asyncio.Semaphore(rate_limit)

        _prompt = (
            "You are an AI documentation assistant, and your task is to summarize the module of project and formulate for which purpose it was written."
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

        _summaries = {}

        async def summarize_directory(name: str, file_summaries: List[str], submodule_summaries: List[str]) -> str:
            """
            This method performs async http request to the LLM server and generates summary for given submodule.

            Args:
                name: submodule (directory) name in current project
                file_summaries: list of file descriptions which the submodule contains
                submodule_summaries: list of nested subdirectories summaries which the submodule contains

            Returns:
                str
            """
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

            async with semaphore:
                return await self.model_handler.async_request(
                    _prompt.format(components=components, main_idea=self.main_idea)
                )

        async def traverse_and_summarize(path: Path, project: dict) -> str:

            _exclusions = (".git", ".github", "test", "tests", "osa_docs")
            _coroutines = []

            leaves_summaries = []

            directories = [d for d in os.listdir(path) if os.path.isdir(Path(path, d)) and d not in _exclusions]
            files = [f for f in os.listdir(path) if not (os.path.isdir(Path(path, f)))]

            for name in directories:
                p = Path(path, name)

                _coroutines.append(traverse_and_summarize(p, project))

            for name in files:
                p = Path(path, name)

                if str(p) in project:
                    leaves_summaries.append(
                        self.format_structure_openai_short(filename=p.name, structure=project[str(p)])
                    )

            folder_summaries = await asyncio.gather(*_coroutines)
            folder_summaries = [s for s in folder_summaries if s]

            if leaves_summaries or folder_summaries:
                summary = (
                    self.main_idea
                    if path == self.config_manager.get_git_settings().name
                    else await summarize_directory(Path(path).name, leaves_summaries, folder_summaries)
                )
                _summaries[str(path)] = summary

                return summary

        await traverse_and_summarize(self.config_manager.get_git_settings().name, project_structure)
        return _summaries

    @staticmethod
    def convert_path_to_dot_notation(path):
        """
        Converts a file system path to a dot notation string for documentation.
        
        This method is used to transform a file path into a format suitable for documentation tools (like MkDocs or Sphinx) that reference modules using dot notation. It strips file extensions and omits "__init__" parts to produce a clean module path.
        
        Args:
            path: The file path to convert, either as a string or a Path object.
        
        Returns:
            A string in the format "::: dot.path.to.module" representing the converted module path. The ":::" prefix is a common directive used in documentation generators to indicate a module reference.
        """
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
        Generates MkDocs documentation for a Python project based on the provided path.
        
        This method creates a structured MkDocs documentation site by processing the project's files and modules. It prepares the repository by renaming invalid directories and adding missing __init__.py files, then generates Markdown documentation files from Python source files and module information. Finally, it copies a predefined MkDocs configuration template to the project. The method is designed to automate the setup of project documentation in a standardized format.
        
        Args:
            path: The path to the root directory of the Python project.
            files_info: A dictionary containing information about Python files to document, where each key is a file path and the value includes a "structure" key indicating whether to process the file.
            modules_info: A dictionary mapping module paths to content strings used to generate index.md files for each module.
        
        Returns:
            None. The method generates MkDocs documentation files and configuration in the project directory.
        """
        local = False
        repo_path = Path(path).resolve()
        mkdocs_dir = repo_path
        self._rename_invalid_dirs(repo_path)
        self._add_init_files(repo_path)

        init_doc_path = Path(repo_path, "osa_docs")
        if init_doc_path.exists():
            shutil.rmtree(init_doc_path)
        init_doc_path.mkdir(parents=True)
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

    def create_mkdocs_git_workflow(self, repository_url: str, path: str) -> None:
        """
        Generates a CI/CD workflow configuration file for deploying MkDocs documentation to the chosen Git hosting service (GitHub or GitLab).
        
        WHY: This method automates the setup of documentation deployment pipelines by creating service-specific YAML workflow files based on a template configuration, ensuring consistent and automated documentation updates.
        
        Parameters:
            repository_url: URI of the project's repository (used for logging guidance about GitHub Pages setup).
            path: Root directory of the Python project where the workflow file will be placed.
        
        Returns:
            None. The method writes a workflow file to the project directory and logs instructions for the user.
        
        Details:
            - For GitHub: Creates `.github/workflows/osa_mkdocs.yml` with the predefined workflow from the template and logs steps to enable GitHub Pages deployment.
            - For GitLab: Creates or updates `.gitlab-ci.yml` by merging MkDocs build and deploy stages into the existing CI configuration, preserving existing stages and adding new ones as needed. Artifacts from the build stage expire after one week.
            - The workflow configuration is read from a template TOML file (`ci_config.toml`) located in the docs/templates directory of the OSA project root.
        """
        config_file = osa_project_root().resolve() / "docs" / "templates" / "ci_config.toml"
        git_host = self.config_manager.get_git_settings().host

        with open(config_file, "rb") as f:
            cfg = tomli.load(f)

        if git_host == "github":
            workflows_path = Path(path).resolve() / ".github" / "workflows"
            workflows_path.mkdir(parents=True, exist_ok=True)
            github_workflow_file = workflows_path / "osa_mkdocs.yml"
            github_workflow_file.write_text(cfg["github"]["workflow"])
            logger.info(f"GitHub workflow created: {github_workflow_file}")
            logger.info(
                f"In order to perform the documentation deployment automatically, please make sure that\n1. At {repository_url}/settings/actions following permission are enabled:\n\t1) 'Read and write permissions'\n\t2) 'Allow GitHub Actions to create and approve pull requests'\n2. 'gh-pages' branch is chosen as the source at 'Build and deployment' section at {repository_url}/settings/pages ."
            )

        if git_host == "gitlab":
            gitlab_cfg = cfg.get("gitlab", {})
            gitlab_file = Path(path).resolve() / ".gitlab-ci.yml"

            if gitlab_file.exists():
                gitlab_data = yaml.safe_load(gitlab_file.read_text()) or {}
            else:
                gitlab_data = {}

            stages: list = gitlab_data.get("stages", [])
            for section in ("build", "deploy"):
                stage_name = gitlab_cfg[section]["stage"]
                if stage_name not in stages:
                    stages.append(stage_name)
            gitlab_data["stages"] = stages

            gitlab_data["mkdocs_build"] = {
                "stage": gitlab_cfg["build"]["stage"],
                "image": f"python:{gitlab_cfg['build']['python_version']}",
                "before_script": gitlab_cfg["build"]["before_script"],
                "script": gitlab_cfg["build"]["script"],
                "artifacts": {
                    "paths": gitlab_cfg["build"]["artifacts"]["paths"],
                    "expire_in": gitlab_cfg["build"]["artifacts"]["expire_in"],
                },
                "rules": gitlab_cfg["build"]["rules"],
            }

            gitlab_data["pages"] = {
                "stage": gitlab_cfg["deploy"]["stage"],
                "image": f"python:{gitlab_cfg['deploy']['python_version']}",
                "before_script": gitlab_cfg["deploy"]["before_script"],
                "script": gitlab_cfg["deploy"]["script"],
                "artifacts": {
                    "paths": gitlab_cfg["deploy"]["artifacts"]["paths"],
                },
                "rules": gitlab_cfg["deploy"]["rules"],
            }

            yaml.Dumper.ignore_aliases = lambda *args: True
            gitlab_file.write_text(yaml.safe_dump(gitlab_data, sort_keys=False))
            logger.info(
                f"GitLab CI created: {gitlab_file}.\nThe resulting OSA documentation can be downloaded and reviewed at the 'mkdocs_build' job's artifacts initated by MR.\nIt will be automatically deployed once MR is proceeded into the main branch.\nNote that artifacts of the 'mkdocs_build' job are set to expire in a span of 1 week."
            )

    @staticmethod
    def _sanitize_name(name: str) -> str:
        """
        Sanitize a given name for use as an identifier.
        
        This method replaces any periods in the name with underscores
        and ensures that the name starts with an alphabetic character.
        If the name does not start with an alphabetic character, it
        prepends a 'v' to the name.
        
        This sanitization is necessary because identifiers in many contexts
        (e.g., variable names, file names) cannot start with non‑alphabetic
        characters and periods may have special meaning (such as in file
        extensions or module paths). Replacing periods with underscores
        prevents misinterpretation, and adding a leading 'v' guarantees a
        valid identifier start.
        
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
        
        Directories are processed from deepest to shallowest (nested to parent) to avoid path conflicts
        after renaming. Directories starting with a dot are skipped, and renaming is skipped if the
        new sanitized name already exists to prevent overwriting.
        
        Args:
            repo_path: The path to the repository where directories will be checked and renamed.
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
        
        The method skips directories that are inside a predefined skip list (e.g., "tests")
        to avoid adding __init__.py files in test directories. It also ensures that
        __init__.py files are only created if they do not already exist.
        
        Args:
            repo_path: The path to the repository where the Python files are located.
        
        Returns:
            None
        """
        py_dirs = set()
        skip_dirs = {repo_path / "tests"}

        def is_in_skip_dirs(path: Path) -> bool:
            for skip_dir in skip_dirs:
                try:
                    path.relative_to(skip_dir)
                    return True
                except ValueError:
                    continue
            return False

        for py_file in repo_path.rglob("*.py"):
            if py_file.name != "__init__.py":
                parent = py_file.parent.resolve()
                while parent != repo_path.parent.resolve():
                    if parent == repo_path:
                        break
                    if is_in_skip_dirs(parent):
                        parent = parent.parent.resolve()
                        continue
                    py_dirs.add(parent)
                    parent = parent.parent.resolve()

        for folder in py_dirs:
            init_path: Path = folder / "__init__.py"
            if not init_path.exists():
                init_path.touch()

    @staticmethod
    def _purge_temp_files(path: str):
        """
        Remove temporary files from the specified directory.
        
        This method deletes the 'mkdocs_temp' directory located within the given path if it exists. This is typically used to clean up temporary files after a runtime error or as part of a cleanup routine to ensure a clean state for subsequent operations.
        
        Args:
            path: The path to the repository where the 'mkdocs_temp' directory is located. The method expects this to be a valid directory path.
        
        Returns:
            None
        """
        repo_path = Path(path)
        mkdocs_dir = repo_path / "mkdocs_temp"
        if mkdocs_dir.exists():
            shutil.rmtree(mkdocs_dir)
