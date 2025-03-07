import argparse
import logging
import os
import re
import shutil
import stat
from pathlib import Path


def parse_folder_name(repo_url: str) -> str:
    """Parses the repository URL to extract the folder name.

    Args:
        repo_url: The URL of the GitHub repository.

    Returns:
        The name of the folder where the repository will be cloned.
    """
    return repo_url.rstrip("/").split("/")[-1]


def osa_project_root() -> Path:
    """Returns osa_tool project root folder."""
    return Path(__file__).parent.parent


def update_toml_file(toml_path: str, api: str = "llama", model_name: str = "llama"):
    """Updates the config's file api and model fields

    Args:
        toml_path: The path to the .toml config file.
        api: The api provided via CLI.
        model_name: The model_name provided via CLI.
    """
    with open(toml_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    updated_lines = []
    for line in lines:
        # Update only the relevant fields while keeping the format intact
        line = re.sub(r'^(\s*api\s*=\s*)"[^"]*"', r'\1"' + api + '"', line)
        line = re.sub(r'^(\s*model\s*=\s*)"[^"]*"', r'\1"' + model_name + '"', line)
        updated_lines.append(line)

    with open(toml_path, "w", encoding="utf-8") as file:
        file.writelines(updated_lines)

    logging.info(
        "Successfully updated the .toml file while preserving formatting."
    )


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
        "--save-dir",
        action="store_true",
        help=(
            "Enable saving the repository directory after the script completes.")
    )
    return parser.parse_args()
