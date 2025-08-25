import os
from dotenv import load_dotenv
from langchain.tools.render import render_text_description

CONFIG_PATH = 'OSA/config.env'
load_dotenv(CONFIG_PATH)

from protollm.agents.builder import GraphBuilder
from protollm.connectors import create_llm_connector

from osa_tool.osa_agent.osa_agent_func import execute_console_command, osa_node

tools_rendered = render_text_description([execute_console_command])
osa_desc = (
    "'osa_node' -  LLM-based tool for improving the quality of scientific open source projects and helping create them from scratch. It automates the generation of README, different levels of documentation, CI/CD scripts, etc. It also generates advices and recommendations for the repository"
)
additional_agents_description = (
    osa_desc
)

conf = {
    # maximum number of recursions
    "recursion_limit": 25,
    "configurable": {
        "user_id": "1",
        "visual_model": create_llm_connector(os.environ["VISION_LLM_URL"]),
        "llm": create_llm_connector(
            os.environ['MAIN_LLM_URL']+';'+os.environ['MAIN_LLM_MODEL']
        ),
        "max_retries": 1,
        # list of scenario agents
        "scenario_agents": [
            "osa_node"
        ],
        # nodes for scenario agents
        "scenario_agent_funcs": {
            "osa_node": osa_node
        },
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
                "examples": None,
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


inputs = {"input": "Make refactoring for repo https://github.com/alinzh/search_api_aviasales, article is https://arxiv.org/pdf/1612.00593"}

graph = GraphBuilder(conf)

if __name__ == "__main__":
    for step in graph.stream(inputs, user_id="1"):
        print(step)