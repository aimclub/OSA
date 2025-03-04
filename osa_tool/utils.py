from pathlib import Path
import logging
import re


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
