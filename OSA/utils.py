from pathlib import Path


def parse_folder_name(repo_url: str) -> str:
    """Parses the repository URL to extract the folder name.

    Args:
        repo_url: The URL of the GitHub repository.

    Returns:
        The name of the folder where the repository will be cloned.
    """
    return repo_url.rstrip('/').split('/')[-1]


def osa_project_root() -> Path:
    """Returns OSA project root folder."""
    return Path(__file__).parent.parent
