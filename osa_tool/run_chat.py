import os

from osa_tool.run import load_configuration
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

    # Load prompts
    prompts = PromptLoader()

    print(user_input)


if __name__ == "__main__":
    main()
