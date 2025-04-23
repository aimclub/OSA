import logging
import os
import shutil
from pathlib import Path
from urllib.parse import urlparse

from rich.logging import RichHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)

logger = logging.getLogger("rich")


def parse_folder_name(repo_url: str) -> str:
    """
    Parses the repository URL to extract the folder name.

    Args:
        repo_url: The URL of the GitHub repository.

    Returns:
        The name of the folder where the repository will be cloned.
    """
    return repo_url.rstrip("/").split("/")[-1]


def osa_project_root() -> Path:
    """Returns osa_tool project root folder."""
    return Path(__file__).parent


def get_base_repo_url(repo_url: str) -> str:
    """
    Extracts the base repository URL path from a given GitHub URL.

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


def parse_git_url(repo_url: str) -> tuple[str, str, str, str]:
    """
    Parse repository URL and return host, full name, and project name.

    Args:
        repo_url: The URL of the GitHub repository.

    Returns:
        tuple: host_domain, host, project name and full name.
    """
    parsed_url = urlparse(repo_url)

    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError(f"Unknown scheme provided: {parsed_url.scheme}")

    if not parsed_url.netloc:
        raise ValueError(f"Invalid Git repository URL: {parsed_url}")

    host_domain = parsed_url.netloc
    host = host_domain.split(".")[0].lower()

    path_parts = parsed_url.path.strip("/").split("/")
    full_name = "/".join(path_parts[:2])
    name = path_parts[-1]

    return host_domain, host, name, full_name


def get_repo_tree(repo_path: str) -> str:
    """
    Builds a text representation of the project file tree, excluding the .git directory.

    Args:
        repo_path: Path to the repository being explored.

    Returns:
        str: A text representation of the repository's file tree with relative paths to files and directories,
             excluding the `.git` directory. Each file or directory path is on a new line.

    """
    repo_path = Path(repo_path)
    excluded_extensions = {
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp', '.drawio',  # images
        '.mp4', '.mov', '.avi', '.mkv', '.flv', '.wmv', '.webm',  # videos
        '.csv', '.tsv', '.parquet', '.json', '.xml', '.xls', '.xlsx',  # data files
        '.zip', '.tar', '.gz', '.bz2', '.7z',  # archives
        '.exe', '.dll', '.so', '.bin', '.obj', '.class', '.pkl',  # binaries
        '.pdf'  # documents
    }

    lines = []
    for path in sorted(repo_path.rglob("*")):
        if any(part.lower() in {".git", "log", "logs"} for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in excluded_extensions:
            continue
        rel_path = path.relative_to(repo_path).as_posix()
        lines.append(str(rel_path))
    return "\n".join(lines)


def extract_readme_content(repo_path: str) -> str:
    """
    Extracts the content of the README file from the repository.

    If a README file exists in the repository, it will return its content.
    It checks for both "README.md" and "README.rst" files. If no README is found,
    it returns a default message.

    Args:
        repo_path: Path to the repository being explored.

    Returns:
        str: The content of the README file or a message indicating absence.
    """
    for file in ["README.md", "README_en.rst", "README.rst"]:
        readme_path = os.path.join(repo_path, file)

        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                return f.read()
    else:
        return "No README.md file"
