import os

from dotenv import load_dotenv
from langchain.tools.render import render_text_description

# here shouild me keys:
# VISION_LLM_URL, MAIN_LLM_MODEL, MAIN_LLM_URL,
# SCENARIO_LLM_MODEL, SCENARIO_LLM_URL, OPENAI_API_KEY, ANOTHER_STORAGE_PATH
# GIT_TOKEN
CONFIG_PATH = "OSA/config.env"
load_dotenv(CONFIG_PATH)

from protollm.agents.builder import GraphBuilder
from protollm.connectors import create_llm_connector

from osa_tool.osa_agent.osa_agent_func import execute_console_command, osa_node

tools_rendered = render_text_description([execute_console_command])
osa_desc = "'osa_node' -  LLM-based tool for improving the quality of scientific open source projects and helping create them from scratch. It automates the generation of README, different levels of documentation, CI/CD scripts, etc. It also generates advices and recommendations for the repository"
additional_agents_description = osa_desc

conf = {
    # maximum number of recursions
    "recursion_limit": 25,
    "configurable": {
        "user_id": "1",
        "visual_model": create_llm_connector(os.environ["VISION_LLM_URL"]),
        "llm": create_llm_connector(os.environ["MAIN_LLM_URL"] + ";" + os.environ["MAIN_LLM_MODEL"]),
        "max_retries": 1,
        # list of scenario agents
        "scenario_agents": ["osa_node"],
        # nodes for scenario agents
        "scenario_agent_funcs": {"osa_node": osa_node},
        # descripton for agents tools - if using langchain @tool
        # or description of agent capabilities in free format
        "tools_for_agents": {
            # here can be description of langchain web tools (not TavilySearch)
            # "web_serach": [web_tools_rendered],
            "osa_node": [tools_rendered],
        },
        # here can be langchain web tools (not TavilySearch)
        # "web_tools": web_tools,
        # full descripton for agents tools
        "tools_descp": tools_rendered + additional_agents_description,
        # set True if you want to use web search like black-box
        "web_search": True,
        # add a key with the agent node name if you need to pass something to it
        "additional_agents_info": {
            "osa_node": {
                "model_name": os.environ["SCENARIO_LLM_MODEL"],
                "url": os.environ["SCENARIO_LLM_URL"],
                "api_key": os.environ["OPENAI_API_KEY"],
                #  Change on your dir if another!
                "ds_dir": os.environ["ANOTHER_STORAGE_PATH"],
            },
        },
        # These prompts will be added in ProtoLLM
        "prompts": {
            "supervisor": {
                "problem_statement": None,
                "problem_statement_continue": None,
                "rules": None,
                "additional_rules": None,
                "examples": None,
                "enhancemen_significance": None,
            },
            "planner": {
                "problem_statement": None,
                "rules": """Don't plan more than 2 tasks! Almost always plan only 1 task. Only if the text is huge use 2.""",
                "desc_restrictions": None,
                "examples": """   
        Request: "Refactor the code in the repository https://github.com/alinzh/dreamstime. Article is https://arxiv.org/pdf/1612.00593."
        Response: {{
            "steps": [
                ["Refactor the code in the repository https://github.com/alinzh/dreamstime, use article https://arxiv.org/pdf/1612.00593 as reference."]
            ]
        }}
        
        Example:
        Request: "Refactor repo https://github.com/avb/vns, paper: https://arxiv.org/pdf/1612.008883."
        Response: {{
            "steps": [
                ['Refactor repository https://github.com/avb/vns, use paper from link https://arxiv.org/pdf/1612.008883.']
            ]
            
        Example:
        Request: "Refactor repo https://github.com/avb/vns, paper: https://arxiv.org/pdf/1612.008883. And, please, make same for project https://github.com/avb/optuna."
        Response: {{
            "steps": [
                ['Refactor repository https://github.com/avb/vns, use paper from link https://arxiv.org/pdf/1612.008883.'], ['Refactor repository https://github.com/avb/optuna']
            ]
        }}""",
                "additional_hints": None,
            },
            "chat": {
                "problem_statement": None,
                "additional_hints": """You are a OSA (Open-Source-Advisor). You are a LLM-based tool for improving the quality of scientific open source projects and helping create them from scratch. It automates the generation of README, different levels of documentation, CI/CD scripts, etc. It also generates advices and recommendations for the repository.
                    """,
            },
            "summary": {
                "problem_statement": None,
                "rules": None,
                "additional_hints": "",
            },
            "replanner": {
                "problem_statement": None,
                "rules": None,
                "examples": None,
                "additional_hints": "If the task is completed, try to return the final answer.",
            },
        },
    },
}


graph = GraphBuilder(conf)

if __name__ == "__main__":
    while True:
        print("Enter your task:")
        for step in graph.stream({"input": input()}, user_id="1"):
            print(step)
