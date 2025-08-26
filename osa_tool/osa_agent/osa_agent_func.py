import shlex
import subprocess
import time
from typing import Annotated

from langchain.tools import tool
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

osa_prompt = """You are an expert system administrator and command line tool. Your task is to execute commands in the system console to solve the given problem.

Follow these steps:
1. Analyze the problem carefully
2. Determine the appropriate console command to solve it
3. Use the execute_console_command tool to run the command
4. Return both the command and the execution results

Important guidelines:
- Only execute safe and appropriate commands
- Prefer cross-platform commands when possible
- Be aware of the current working directory and environment
- Handle potential errors gracefully

Avalible flags:
Parameter	Aliases	Type	Description	Default	Choices
repository	-r, --repository	str	URL of the GitHub repository	https://github.com/aimclub/OSA	—
branch	-b, --branch	str	Branch name of the GitHub repository	null	—
article	--article	str	README template for a repository with an article, or a link to a PDF file	null	—
translate-dirs	--translate-dirs	flag	Enable automatic translation of directory names into English	false	—
convert-notebooks	--convert-notebooks	list	Convert Jupyter notebooks to .py format. Provide paths, or leave empty for repo directory	—	—
delete-dir	--delete-dir	flag	Delete the downloaded repository after processing	false	—
ensure-license	--ensure-license	str	Enable LICENSE file compilation	null	bsd-3, mit, ap2
no-fork	--no-fork	flag	Do not create a public fork to the target repository	false	—
no-pull-request	--no-pull-request	flag	Do not create a pull request to the target repository	false	—
community-docs	--community-docs	flag	Generate community-related documentation files	false	—
docstring	--docstring	flag	Automatically generate docstrings for Python files	false	—
report	--report	flag	Analyze the repository and generate a PDF report	false	—
readme	--readme	flag	Generate a README.md file based on repository content	false	—
organize	--organize	flag	Organize the repository by adding standard tests and examples directories if missing	false	—
about	--about	flag	Generate About section with tags	false	—
generate-workflows	--generate-workflows	flag	Generate GitHub Action workflows for the repository	false	—
workflows-output-dir	--workflows-output-dir	str	Directory where workflow files will be saved	.github/workflows	—
include-tests	--include-tests	flag	Include unit tests workflow	true	—
include-black	--include-black	flag	Include Black formatter workflow	true	—
include-pep8	--include-pep8	flag	Include PEP 8 compliance workflow	true	—
include-autopep8	--include-autopep8	flag	Include autopep8 formatter workflow	false	—
include-fix-pep8	--include-fix-pep8	flag	Include fix-pep8 command workflow	false	—
include-pypi	--include-pypi	flag	Include PyPI publish workflow	false	—
python-versions	--python-versions	list	Python versions to test against	[3.9, 3.10]	—
pep8-tool	--pep8-tool	str	Tool to use for PEP 8 checking	flake8	flake8, pylint
use-poetry	--use-poetry	flag	Use Poetry for packaging	false	—
branches	--branches	list	Branches to trigger workflows on	[]	—
codecov-token	--codecov-token	flag	Use Codecov token for coverage upload	false	—
include-codecov	--include-codecov	flag	Include Codecov coverage step in unit tests workflow	true	—
top-p	--top-p	str	Nucleus sampling probability	null	—
temperature	--temperature	str	Sampling temperature to use for the LLM output (0 = deterministic, 1 = creative).	null	—
max-tokens	--max-tokens	str	Maximum number of tokens the model can generate in a single response	1500	—

Don't invent new flags! Only these!
You must use '--web-mode' in every command!

Example of full commands:
'python3.11 -m osa_tool.run -r https://github.com/tall/raw_convertor --web-mode'
'python3.11 -m osa_tool.run -r https://github.com/tall/raw_convertor -m basic --web-mode --max-tokens 10000'
'python3.11 -m osa_tool.run -r https://github.com/tilde/sql_vis -m basic --web-mode --article https://arxiv.org/pdf/1612.00593'
Current task: {input}

Remember to call the execute_console_command tool with your command!"""


@tool
def execute_console_command(command: str) -> str:
    """
    Run OSA from cli. Is a LLM-based tool for improving the quality of 
    scientific open source projects and helping create them from scratch. 
    It automates the generation of README, different levels of documentation, 
    CI/CD scripts, etc. It also generates advices and recommendations 
    for the repository.

    Parameters:
    command (str): Console command to execute

    Returns:
    str: Command output including both stdout and stderr
    """
    try:
        if isinstance(command, str):
            command_args = shlex.split(command)
        else:
            command_args = command

        result = subprocess.run(command_args, capture_output=True, text=True, timeout=120)

        output = result.stdout
        if result.stderr:
            output += f"\nErrors:\n{result.stderr}"

        return output

    except subprocess.TimeoutExpired:
        return "Execution timed out after 30 seconds"
    except Exception as e:
        return f"Failed to execute command: {str(e)}"


def osa_node(state: dict, config: dict):
    """
    Executes OSA modules using a language model (LLM) and predefined OSA tools.
    Now includes ability to execute console commands.
    """
    llm = config["configurable"]["llm"]
    max_retries = config["configurable"]["max_retries"]

    agent = create_react_agent(llm, [execute_console_command], prompt=osa_prompt)
    task = state["task"]

    for attempt in range(max_retries):
        try:
            agent_response = agent.invoke(
                {"messages": [("user", task + " Execute appropriate console commands to solve this!")]}
            )
            for i, m in enumerate(agent_response["messages"]):
                if m.content == []:
                    agent_response["messages"][i].content = ""
            return Command(
                update={
                    "past_steps": Annotated[set, "or_"]({(task, agent_response["messages"][-1].content)}),
                    "nodes_calls": Annotated[set, "or_"](
                        {
                            (
                                "osa_agent",
                                tuple((m.type, m.content) for m in agent_response["messages"]),
                            )
                        }
                    ),
                }
            )
        except Exception as e:
            print(f"OSA Agent failed: {str(e)}. Retrying ({attempt+1}/{max_retries})")
            time.sleep(1.2**attempt)
