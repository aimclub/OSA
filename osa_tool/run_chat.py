import os
import time

from osa_tool.config.osa_config import OSAConfig
from osa_tool.config.settings import ConfigManager
from osa_tool.osa_agent.context import AgentContext
from osa_tool.osa_agent.graph import build_graph
from osa_tool.osa_agent.state import AgentStatus, OSAState
from osa_tool.run import initialize_git_platform
from osa_tool.ui.input_for_chat import InitialChatInput, collect_user_input
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import setup_logging
from osa_tool.utils.utils import osa_project_root, parse_folder_name, switch_to_output_directory


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

    # Switch to output directory if present
    if args.output:
        switch_to_output_directory(args.output)

    # Initialize infrastructure
    args.repository = user_input.repo_url
    config_manager = ConfigManager(args)
    git_agent, workflow_manager = initialize_git_platform(args)

    agent_config = OSAConfig(
        config_manager=config_manager,
        git_agent=git_agent,
        workflow_manager=workflow_manager,
        create_fork=not args.no_fork,
        create_pull_request=not args.no_pull_request,
        enable_replanning=True,
        enable_memory=True,
    )
    context = AgentContext(agent_config)

    # Create initial state from user input
    initial_state = OSAState(
        repo_url=user_input.repo_url,
        user_request=user_input.user_request,
        attachment=user_input.attachment,
        session_id=f"session_{int(time.time())}",
        status=AgentStatus.INIT,
    )

    # Create the graph
    graph = build_graph(context)

    # Execute the graph
    result_state_dict = graph.invoke(initial_state)
    result_state = OSAState.model_validate(result_state_dict)

    print("Result plan:")
    print(result_state.plan)


if __name__ == "__main__":
    main()
