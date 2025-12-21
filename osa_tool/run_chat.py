import os
import time
from typing import List

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.osa_agent.builder import create_agent_graph
from osa_tool.osa_agent.config import OSAAgentConfig, ToolSpec
from osa_tool.osa_agent.nodes.planner_node import OSAPlannerNode
from osa_tool.osa_agent.state import OSAAgentState, AgentStatus
from osa_tool.run import load_configuration, initialize_git_platform
from osa_tool.ui.input_for_chat import InitialChatInput, collect_user_input
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import setup_logging
from osa_tool.utils.prompts_builder import PromptLoader
from osa_tool.utils.utils import osa_project_root, parse_folder_name


def main():
    # Create a command line argument parser
    parser = build_parser_from_yaml(extra_sections=["settings"])
    args = parser.parse_args()

    # Collecting user parameters
    user_input: InitialChatInput = collect_user_input()

    # Initialize logging
    logs_dir = os.path.join(os.path.dirname(osa_project_root()), "logs")
    repo_name = parse_folder_name(user_input.repo_url)
    setup_logging(repo_name, logs_dir)

    # Load configurations and update
    args.repository = user_input.repo_url
    config_loader = load_configuration(args)

    # Initialize GitAgent and SourceRank
    git_agent, _ = initialize_git_platform(args)
    sourcerank = SourceRank(config_loader)

    # Load prompts
    prompts = PromptLoader()

    agent_config = OSAAgentConfig(
        config_loader=config_loader,
        git_agent=git_agent,
        sourcerank=sourcerank,
        enable_replanning=True,
        enable_memory=True,
        prompts=prompts,
        tools=_create_temp_tool_specs(),
        scenario_agents=["planner_node"],
        scenario_agents_funcs={"planner_node": OSAPlannerNode},
    )

    # Create initial state from user input
    initial_state = OSAAgentState(
        repo_url=user_input.repo_url,
        user_request=user_input.user_request,
        attachment=user_input.attachment,
        session_id=f"session_{int(time.time())}",
        status=AgentStatus.INIT,
        repo_metadata=git_agent.metadata,
    )

    # Create the graph
    graph = create_agent_graph(agent_config)

    # Execute the graph
    result_state_dict = graph.invoke(initial_state)
    print(result_state_dict)

    result_state = OSAAgentState.model_validate(result_state_dict)

    print(f"Generated plan: {result_state.tasks}")
    print(f"Status: {result_state.status}")


def _create_temp_tool_specs() -> List[ToolSpec]:
    """
    Create temporary ToolSpec objects for planning.
    These will be replaced with actual tools when the system is complete.
    """
    return [
        ToolSpec(
            name="analyze_repository",
            description="Analyze repository structure, files, and overall organization",
            args_schema={
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string", "description": "Repository URL"},
                },
                "required": ["repo_url"],
            },
        ),
        ToolSpec(
            name="generate_readme",
            description="Generate comprehensive README.md for the repository based on analysis",
            args_schema={
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string", "description": "Repository URL"},
                    "article": {"type": "string", "description": "Additional article content"},
                    "refine_readme": {
                        "type": "boolean",
                        "default": False,
                        "description": "Whether to refine existing README",
                    },
                },
                "required": ["repo_url"],
            },
        ),
        ToolSpec(
            name="generate_requirements",
            description="Generate requirements.txt or requirements.yml based on repository dependencies",
            args_schema={
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string", "description": "Repository URL"},
                },
                "required": ["repo_url"],
            },
        ),
        ToolSpec(
            name="translate_readme",
            description="Translate README to target language(s)",
            args_schema={
                "type": "object",
                "properties": {
                    "repo_url": {"type": "string", "description": "Repository URL"},
                    "target_language": {
                        "type": "string",
                        "description": "Target language for translation (e.g., 'English', 'Russian', 'Chinese') or list of languages",
                    },
                },
                "required": ["repo_url", "target_language"],
            },
        ),
    ]


if __name__ == "__main__":
    main()
