# Research analyze of the documentation generating tools

1. **Autodoc** ([context-labs/autodoc: Experimental toolkit for auto-generating codebase documentation using LLMs](https://github.com/context-labs/autodoc)). MIT license. According to the repo's readme: 

   1. JS-project. 

   2. Unstable, early-stage of development. 

   3. Prompt-sensitive tool, a particular need for a specific type of question is in demand in order to provide a suitable and correct response. 

   4. Although it currently works exclusively with OpenAI API the project is also orienting towards local LLM support as well, to be more specific Llama and Alpaca. 

   5. If code repo is indexed under 4K tokens it would be processed using GPT-3.5 which will bring less accurate documentation. 

   6. Uses “doc” cli-command to enter the chat where the model will compose a suitable answer for the submitted question and provide it with the description on the particular part and reference links to the codebase elements the query conducted.

2. **Doc-Comments-AI** ([fynnfluegge/doc-comments-ai: LLM-powered code documentation generation](https://github.com/fynnfluegge/doc-comments-ai)). MIT license. 

   1. Python based project. 

   2. Generating commentary blocks before every module in the project. 

   3. Supports both Open AI and local LLMs. 

   4. A wide variety of the supported languages. 

   5. By default uses GPT-3.5. 

   6. From the example from the project’s readme the toolkit processing and indexing every file in the project and then contributing to them via adding commentary section blocks that do not provide a verbose description on how each module works with only general info presenting.

3. **ReadTheDocs** (site: [Full featured documentation deployment platform \- Read the Docs](https://about.readthedocs.com/?ref=readthedocs.org) repo: [readthedocs/readthedocs.org: The source code that powers readthedocs.org](https://github.com/readthedocs/readthedocs.org/tree/main)).

   1. Currently does not use any LLM.

   2. All of the documentation is pre-made by the developers. 

   3. Sphinx tool automatically converts reStructuredText and markdown file formats into web-friendly ones and deploys them as documentation projects.

   4. Elaborates the conception of the “Continuous Documentation” or “Docs as the Code” approach.

   5. Has a dashboard control instrument for better user experience.

4. **Flake8** ([PyCQA/flake8: flake8 is a python tool that glues together pycodestyle, pyflakes, mccabe, and third-party plugins to check the style and quality of some python code.](https://github.com/PyCQA/flake8)).

   1. Does not use any LLM.

   2. All of the documentation is premade by users.

   3. Tool is linking reStructuredText files into a single project.