import os
import platform
import shutil
from pathlib import Path

import git
from readmegen.errors import GitCloneError
from readmegen.logger import get_logger
from readmegen.preprocessor.directory_cleaner import (
    remove_directory,
    remove_hidden_contents,
)

_logger = get_logger(__name__)


def clone_repository(
        repo_url: str,
        target: Path,
        depth: int = 1
) -> None:
    """
    Clone a Git repository to the specified target directory.

    :param repo_url: URL repository.
    :param target: path where to clone.
    :param depth: cloning depth (default 1).
    """

    git.Repo.clone_from(
        repo_url,
        str(target),
        depth=depth,
        single_branch=True
    )


def copy_directory(source: Path, target: Path) -> None:
    """Copy a directory and its contents to a new location.

    :param source: path from where to copy
    :param target: path where to copy
    """

    if platform.system() == "Windows":
        os.system(f'xcopy "{source}" "{target}" /E /I /H /Y')
    else:
        shutil.copytree(
            source,
            target,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns(".git"),
        )


def load_data(repository: Path | str, temp_dir: str) -> str:
    temp_dir_path = Path(temp_dir)
    repo_path = Path(repository)

    try:
        if temp_dir_path.exists():
            remove_directory(temp_dir_path)

        if repo_path.is_dir():
            copy_directory(repo_path, temp_dir_path)
        else:
            clone_repository(str(repository), temp_dir_path)

        remove_hidden_contents(temp_dir_path)

        return str(temp_dir_path)
    except Exception as e:
        _logger.error(
            f"Unexpected error while cloning repository {repository}: {e}",
        )
        raise GitCloneError(
            f"Unexpected error while cloning repository {repository}",
        ) from e
