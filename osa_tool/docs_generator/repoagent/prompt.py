from llama_index.core import ChatPromptTemplate
from llama_index.core.llms import ChatMessage, MessageRole

docstring_generation_instruction = (
    """Generate a Google-formatted docstring for the Python {code_type_tell} located at {file_path}. 
The {code_type_tell} is named {code_name} and has the following code content:

```python
{code_content}  
```
{reference_letter}

{referencer_content}

{main_idea}

Follow these rules:

Structure: Include sections like Args, Returns, Raises, Examples (if applicable), and Notes (if references exist).

Style:

Use triple double quotes.

Write concise, present-tense, third-person descriptions.

DO NOT list methods for class docstring.

For functions/methods, list parameters, return types, exceptions, and examples (in code blocks with >>>).

Do NOT invent parameters/attributes/methods not in the code.

Prioritize type hints and good docstrings from the code.

DO NOT conv

Example Output Structure:

```python
[Short one-line description].  

[Longer description if needed.]

Args:  
    param1 (type): Description. Defaults to X.  
    param2 (type): Description.  

Returns:  
    type: Description.  

Raises:  
    ValueError: If [condition].  

Note:  
    See also: [referencer_content] (if applicable).  
```

Focus: Ensure accuracy, adherence to Google conventions, and consistency with the provided code structure."

Notes:

For ClassDef objects put only description section

Do not add methods descriptions for class docstrings.

Return docstring as plaintext - do not put it in any ``` or triple double quotes. 

Do not put too much examples and references.

Replace {code_type_tell} with "function", "method", or "class".

Keep in mind that your audience is document readers, so use a deterministic tone to generate precise content and don't let them know you're provided with code snippet and documents. AVOID ANY SPECULATION and inaccurate descriptions!"""
)

docstring_system = (
    "You are python senior developer. You are developer of the framework"
)

message_templates = [
    ChatMessage(content=docstring_system, role=MessageRole.SYSTEM),
    ChatMessage(content=docstring_generation_instruction, role=MessageRole.USER),

]

chat_template = ChatPromptTemplate(message_templates=message_templates)

docstring_update_instruction = (
    """Update a Google-formatted docstring for the Python {code_type_tell} located at {file_path} uding provided main idea of the project. Note that you will not be provided with any code
The {code_type_tell} is named {code_name} and has the following docstring:

```python
{docstring}
```

{main_idea}

Follow these rules:

Structure: Include sections like Args, Returns, Raises, Examples (if applicable), and Notes (if references exist).

Style:

Write concise, present-tense, third-person descriptions.

DO NOT list methods for class docstring.

For functions/methods, list parameters, return types, exceptions, and examples (in code blocks with >>>).

Do NOT invent parameters/attributes/methods not in the code.

Prioritize type hints and good docstrings from the code.

Example Output Structure:

```python
[Short one-line description].  

[Longer description if needed.]

Args:  
    param1 (type): Description. Defaults to X.  
    param2 (type): Description.  

Returns:  
    type: Description.  

Raises:  
    ValueError: If [condition].  

Note:  
    See also: [referencer_content] (if applicable).  
```

Focus: Ensure accuracy, adherence to Google conventions, and consistency with the provided code structure."

Notes:

For ClassDef objects put only description section

Return docstring as plaintext - do not put it in any ``` or triple double quotes. 

Do not put too much examples and references.

Replace {code_type_tell} with "function", "method", or "class".

Keep in mind that your audience is document readers, so use a deterministic tone to generate precise content and don't let them know you're provided with code snippet and documents. AVOID ANY SPECULATION and inaccurate descriptions!"""
)

docstring_update_templates = [
    ChatMessage(content=docstring_system, role=MessageRole.SYSTEM),
    ChatMessage(content=docstring_update_instruction, role=MessageRole.USER),

]

docstring_update_chat_templates = ChatPromptTemplate(message_templates=docstring_update_templates)

idea_generation_instruction = (
    "You are an AI documentation assistant, and your task is to summarize the main idea of the project and formulate for which purpose it was written."
    "You are given with the list of the main components (classes and functions) with it's short description and location in project hierarchy:\n"
    "{components}\n"
    "Formulate only main idea without describing components. DO NOT list components, just return overview of the project and it's purpose.\n"
    "Format you answer in a way you're writing markdown README file"
)

idea_generation_guideline = (
    "Keep in mind that your audience is document readers, so use a deterministic tone to generate precise content and don't let them know "
    "you're provided with any information. AVOID ANY SPECULATION and inaccurate descriptions! Now, provide the summarized idea of the project based on it's components"
    " in {language} in a professional way."
)

idea_message_templates = [
    ChatMessage(content=idea_generation_instruction, role=MessageRole.SYSTEM),
    ChatMessage(
        content=idea_generation_guideline,
        role=MessageRole.USER,
    ),
]

idea_chat_template = ChatPromptTemplate(message_templates=idea_message_templates)

new_description_generation_instruction = (
    "You are an AI documentation assistant, and your task is update the description part of existing documentation "
    "based on the new information (main idea of the project):\n"
    "{main_idea}\n"
    "The initial documentation page is:\n"
    "{init_doc}\n"
    "You should replace only tis part:"
    "----------"
    "{doc_desc}"
    "----------"
    " You should return only new content which will replace existing content. Do not explicit the main idea. If main idea cannot help to enhance desctiption - do not change it."
    " Write mainly in the desired language. If necessary, you can write with some English words in the analysis and description "
    "to enhance the document's readability because you do not need to translate the function name or variable name into the target language.\n"
)

new_description_guideline = (
    "Keep in mind that your audience is document readers, so use a deterministic tone to generate precise content and don't let them know "
    "you're provided with code snippet and documents. AVOID ANY SPECULATION and inaccurate descriptions! "
    "Now, provide the updated documentation section "
    "for the target object in {language} in a professional way."
)

desc_message_templates = [
    ChatMessage(content=new_description_generation_instruction, role=MessageRole.SYSTEM),
    ChatMessage(
        content=new_description_guideline,
        role=MessageRole.USER,
    ),
]

new_desc_chat_template = ChatPromptTemplate(message_templates=desc_message_templates)

module_summary_generation_instruction = (
    "You are an AI documentation assistant, and your task is to summarize the module of project and formulate for which purpose it was written."
    "You are given with the list of the components (classes and functions or submodules) with it's short description:\n\n"
    "{components}\n\n"
    "Also you have the snippet from README file of project from this module has came describing the main idea of the whole project:\n\n"
    "{main_idea}\n\n"
    "You should generate markdown-formatted documentation page describing this module using description of all files and all submodules.\n"
    "Do not too generalize overview and purpose parts using main idea. Concentrate on local module features were infered previously.\n"
    "Format you answer in a way you're writing README file for the module. Use such template:\n\n"
    "# Name\n"
    "## Overview\n"
    "## Purpose\n"

    "Do not mention or describe any submodule or files! Rename snake_case names on meaningful names."
)

module_summary_generation_guideline = (
    "Keep in mind that your audience is document readers, so use a deterministic tone to generate precise content and don't let them know "
    "you're provided with any information. AVOID ANY SPECULATION and inaccurate descriptions! Now, provide the summarized idea of the module based on it's components"
    " in {language} in a professional way."
)

module_summary_message_templates = [
    ChatMessage(content=module_summary_generation_instruction, role=MessageRole.SYSTEM),
    ChatMessage(
        content=module_summary_generation_guideline,
        role=MessageRole.USER,
    ),
]

module_summary_template = ChatPromptTemplate(message_templates=module_summary_message_templates)
