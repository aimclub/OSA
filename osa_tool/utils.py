import logging
import os
import shutil
from pathlib import Path

from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)

logger = logging.getLogger("rich")


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


def get_base_repo_url(repo_url: str) -> str:
    """Extracts the base repository URL path from a given GitHub URL.

    Args:
        repo_url (str, optional): The GitHub repository URL. If not provided,
            the instance's `repo_url` attribute is used. Defaults to None.

    Returns:
        str: The base repository path (e.g., 'username/repo-name').

    Raises:
        ValueError: If the provided URL does not start with 'https://github.com/'.
    """
    if repo_url.startswith("https://github.com/"):
        return repo_url[len("https://github.com/"):].rstrip('/')
    else:
        raise ValueError("Unsupported repository URL format.")


def delete_repository(repo_url: str) -> None:
    """
    Deletes the local directory of the downloaded repository based on its URL.

    Args:
        repo_url (str): The URL of the repository to be deleted.

    Raises:
        Exception: Logs an error message if deletion fails.
    """
    repo_path = os.path.join(os.getcwd(), parse_folder_name(repo_url))
    try:
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path)
            logger.info(f"Directory {repo_path} has been deleted.")
        else:
            logger.info(f"Directory {repo_path} does not exist.")
    except Exception as e:
        logger.error(f"Failed to delete directory {repo_path}: {e}")
