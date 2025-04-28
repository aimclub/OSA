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
        choices=["llama", "openai", "ollama"],
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
            "2. https://platform.openai.com/docs/models\n"
            "3. https://ollama.com/library"
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
        "--convert-notebooks",
        type=str,
        help=(
            "Convert Jupyter notebooks from .ipynb to .py format.\n"
            "You can provide one or multiple paths to files or directories.\n"
            "If no paths are provided, the repo directory will be used."
        ),
        nargs='*',
    )
    parser.add_argument(
        "--delete-dir",
        action="store_true",
        help="Enable deleting the downloaded repository after processing. ("
             "Linux only)"
    )
    parser.add_argument(
        "--ensure-license",
        nargs='?',
        const="bsd-3",
        default=None,
        help="Enable LICENSE file compilation"
    )

    # Create a group for GitHub workflow generator arguments
    workflow_group = parser.add_argument_group('GitHub workflow generator arguments')
    workflow_group.add_argument(
        "--generate-workflows",
        action="store_true",
        help="Generate GitHub Action workflows for the repository"
    )
    workflow_group.add_argument(
        "--workflows-output-dir",
        type=str,
        default=".github/workflows",
        help="Directory where the workflow files will be saved"
    )
    workflow_group.add_argument(
        "--include-tests",
        action="store_true",
        default=True,
        help="Include unit tests workflow"
    )
    workflow_group.add_argument(
        "--include-black",
        action="store_true",
        default=True,
        help="Include Black formatter workflow"
    )
    workflow_group.add_argument(
        "--include-pep8",
        action="store_true",
        default=True,
        help="Include PEP 8 compliance workflow"
    )
    workflow_group.add_argument(
        "--include-autopep8",
        action="store_true",
        default=False,
        help="Include autopep8 formatter workflow"
    )
    workflow_group.add_argument(
        "--include-fix-pep8",
        action="store_true",
        default=False,
        help="Include fix-pep8 command workflow"
    )
    workflow_group.add_argument(
        "--include-pypi",
        action="store_true",
        default=False,
        help="Include PyPI publish workflow"
    )
    workflow_group.add_argument(
        "--python-versions",
        type=str,
        nargs="+",
        default=["3.8", "3.9", "3.10"],
        help="Python versions to test against"
    )
    workflow_group.add_argument(
        "--pep8-tool",
        type=str,
        choices=["flake8", "pylint"],
        default="flake8",
        help="Tool to use for PEP 8 checking"
    )
    workflow_group.add_argument(
        "--use-poetry",
        action="store_true",
        default=False,
        help="Use Poetry for packaging"
    )
    workflow_group.add_argument(
        "--branches",
        type=str,
        nargs="+",
        default=[],
        help="Branches to trigger the workflows on"
    )
    workflow_group.add_argument(
        "--codecov-token",
        action="store_true",
        default=False,
        help="Use Codecov token for uploading coverage"
    )
    workflow_group.add_argument(
        "--include-codecov",
        action="store_true",
        default=True,
        help="Include Codecov coverage step in a unit tests workflow."
    )
    return parser.parse_args()
