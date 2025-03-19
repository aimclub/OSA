import argparse


def get_cli_args():
    # Create a command line argument parser
    parser = argparse.ArgumentParser(
        description="Generate README.md for a GitHub repository",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-r",
        "--repository",
        type=str,
        help="URL of the GitHub repository",
        required=True,
    )
    parser.add_argument(
        "--api",
        type=str,
        help="LLM API service provider",
        nargs="?",
        choices=["llama", "openai"],
        default="llama",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="URL of the provider compatible with API OpenAI",
        nargs="?",
        default="https://api.openai.com/v1",
    )
    parser.add_argument(
        "--model",
        type=str,
        help=(
            "Specific LLM model to use. "
            "To see available models go there:\n"
            "1. https://vsegpt.ru/Docs/Models\n"
            "2. https://platform.openai.com/docs/models"
        ),
        nargs="?",
        default="gpt-3.5-turbo",
    )
    parser.add_argument(
        "--article",
        type=str,
        help=(
            "Select a README template for a repository with an article.\n"
            "You can also provide a link to the pdf file of the article\n"
            "after the --article option."
        ),
        nargs="?",
        const="",
        default=None,
    )
    parser.add_argument(
        "--translate-dirs",
        action="store_true",
        help=(
            "Enable automatic translation of the directory name into English.")
    )
    parser.add_argument(
        "--delete-dir",
        action="store_true",
        help="Enable deleting the downloaded repository after processing. ("
             "Linux only)"
    )
    return parser.parse_args()
