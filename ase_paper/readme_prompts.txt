Metric evaluation prompt

Determine whether the AI-generated Readme file (ACTUAL_OUTPUT)
is better than the original one (EXPECTED_OUTPUT).
ACTUAL_OUTPUT contains two fields: 'readme', which contains generated README itself,
and 'repo_structure' which is json with repository's structure.
Generated README's content must be consistent with provided repository structure.
The ACTUAL_OUTPUT is not neccessary has to be the same as EXPECTED_OUTPUT,
Your goal is to determine which text is better, using provided Evaluations steps.
Readme structure does not matter much as long as it passes evaluation steps.

"Step 1: Does provided structure of the repository addresses README content?",
"Step 2: Does the README provide a clear and accurate overview
    of the repository's purpose?",
"Step 3: Are installation and setup instructions included and easy to follow?",
"Step 4: Are usage examples provided and do they clearly demonstrate functionality?",
"Step 5: Are dependencies or requirements listed appropriately?",
"Step 6: Is the README easy to read, well-structured, and free of confusing language?",

README style prompts

Pre-analysis prompt

TASK:
Based on the provided data about the files and the README content,
your task is to identify and return the paths to 3-5 key files that
contain the main business logic or project description.
RULES:
- Return one path per line.
- Choose the most important files that define the project’s core logic.
- Exclude files related to tests, configuration,
or assets unless they are central to the business logic.
- Exclude README files.

Core features prompt

TASK:
Based on the provided information about the project,
generate a list of core features for the project.
Each core feature should be represented by JSON format following this structure:
{{
    "feature_name": "text",
    "feature_description": "text",
    "is_critical": boolean
}}
RULES:
- The output should be a JSON array.
- Each element in the array should represent one core feature.
- Use double quotes for JSON formatting.
- Be sure to generate multiple core features,
each describing a different aspect of the project.
- The 'feature_name' should describe a key aspect.
- The 'feature_description' should be a detailed
but short explanation of the feature.

Overview prompt

TASK:
Generate a concise overview of the project by analyzing the provided data.
Your response should be a short paragraph that encapsulates the core use-case,
value proposition.
RULES:
- Focus on the project's core purpose and its value
proposition without mentioning specific technical aspects.
- Avoid technical jargon, code snippets, or any implementation details.
- The overview should be no more than 60 words.

Getting started prompt

TASK:
You are generating the "Getting Started" section
for the README file of the project above.
Your goal is to help a new user understand how to start
using the project by analyzing the provided example files.
If you find a clear entrypoint or demonstration of how to run or integrate
the project - use that information to generate a concise, helpful section.
If the example files are empty, contain only boilerplate code
(e.g., import statements or data definitions), or do not provide any meaningful
insight on how to use the project — return `null` in JSON instead of a section.
RULES:
- Be concise and beginner-friendly.
- Use markdown formatting with code blocks if needed.
- Prefer actual code found in the examples over assumptions.
- DO NOT make up usage instructions — rely only on provided content.
- If unsure or examples are not helpful, return "getting_started": null
- Don't add ## Getting Started at the beginning

Article style prompts

Files summary prompt

TASK:
Analyze the provided code repository. Your task is to summarize the following:
Purpose: The overall goal and intended function of the codebase.
Architecture: The structure of the codebase and its key components.
Functionality: What the code achieves and the main algorithms or approaches
it implements. Connection to the context: How the code reflects or supports
the methodology, key ideas, or results described in the article. Ensure
your summary is clear, concise, and omits technical implementation details.
Focus on high-level insights that help understand the codebase.
RULES:
- Avoid phrases like "This file", "The file", or "This code".
- Begin with a verb or noun.
- Do not include quotes, code snippets, bullets, or lists.
- Limit the response to 200-250 words.

Article summary prompt

TASK:
Analyze the given text, which may be a technical report or article.
Your task is to extract the following,
basing your response solely on the context provided:

Main topic: Identify the central subject of the document.
Key ideas: Highlight the primary concepts or arguments presented.
Methodology: Describe the methods or approaches used.
Working steps: Outline the significant actions or processes involved.
Results: Summarize the outcomes or findings.
Ensure your response is precise, uses concise language, and avoids
any additional information not present in the text.
RULES:
- Start with a strong, attention-grabbing statement.
- Avoid phrases like "This PDF" or "The document".
- Exclude quotes, code snippets, bullets, or lists.
- Limit the response to 200-250 words.

Overview prompt

TASK:
Outline the repository's purpose and objectives based on the following context.
Emphasize main functionalities and goals without technical jargon.
RULES:
- Begin with a clear statement capturing the project's essence.
- Use 150-200 words.
- Avoid phrases like "This project" or "The repository".

Content prompt

TASK:
Describe the repository's components—including databases, models,
and other relevant parts—and explain how they interrelate to support
the project’s functionality.
RULES:
- Emphasize each component's role in the overall project.
- Focus on high-level concepts, avoiding technical details.
- Don't put quotes around or enclose any code.

Algorithms prompt

TASK:
Detail the algorithms used in the codebase, explaining their functions.
RULES:
- Describe each algorithm's role without technical implementation details.
- Use clear, accessible language.

Scheduler prompt

TASK:
Analyze the repository structure and README content to determine
the appropriate settings for the following options.
Generate a JSON report following this exact structure:
{{
  "generate_report": boolean,
  "translate_dirs": boolean,
  "generate_docstring": boolean,
  "ensure_license": str or None,
  "community_docs": boolean,
  "generate_readme": boolean,
  "organize": boolean,
}}

RULES:

- Return only a valid JSON object following exactly the structure above.
- "generate_report": true if an additional user report would be helpful,
false otherwise.
- "translate_dirs": true if directory and file names
need to be translated to English.
- "generate_docstring": true if significant Python code lacks docstrings.
- "ensure_license": one of "bsd-3", "mit", "ap2" if a license
file should be generated, or None if license is alreade presented.
- "community_docs": true if community files like CODE_OF_CONDUCT.md or
PULL_REQUEST_TEMPLATE.md should be created.
- "generate_readme": true if README is missing or of low quality,
false if README is clear and sufficient.
- "organize": true if 'tests' or 'examples' directories are missing and should be added.

- Do not add any explanations, comments or extra text.
- Use lowercase true/false and null exactly as JSON booleans/null.
- Your response must be valid JSON parsable by standard parsers.
