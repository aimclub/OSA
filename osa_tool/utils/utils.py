import json
import os
import re
import shutil
import stat
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console

from osa_tool.utils.logger import logger

console = Console()

KNOWN_FILE_NAMES = {
    "readme",
    "license",
    "copying",
    "citation",
    "contributing",
    "security",
    "code_of_conduct",
    "makefile",
    "dockerfile",
    "jenkinsfile",
}


def rich_section(title: str):
    """
    Print a styled section header in the console to visually separate log sections.

    Args:
        title: Title text for the section header.
    """
    console.print("")
    console.rule(f"[bold cyan]{title}[/bold cyan]", style="cyan")


def _remove_tree(path: str | Path) -> None:
    """Remove a directory tree, retrying read-only files on Windows."""
    target = Path(path)

    def on_rm_error(func, failed_path, exc_info):
        try:
            os.chmod(failed_path, stat.S_IWRITE)
            func(failed_path)
        except Exception as e:
            logger.error(f"Failed to forcibly remove {failed_path}: {e}")

    shutil.rmtree(target, onerror=on_rm_error)


def _looks_like_file_path(relative_path: str) -> bool:
    """
    Best-effort distinction between repository files and directories for browse URLs.
    """
    path = Path(relative_path.replace("\\", "/"))
    name = path.name
    lowered = name.lower()

    if lowered in KNOWN_FILE_NAMES:
        return True

    suffix = path.suffix.lower()
    if not suffix:
        return False

    if lowered.startswith(".") and lowered.count(".") == 1:
        return False

    file_suffixes = {
        ".md",
        ".rst",
        ".txt",
        ".py",
        ".ipynb",
        ".toml",
        ".yaml",
        ".yml",
        ".json",
        ".ini",
        ".cfg",
        ".conf",
        ".xml",
        ".csv",
        ".tsv",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".java",
        ".kt",
        ".go",
        ".rs",
        ".c",
        ".cc",
        ".cpp",
        ".h",
        ".hpp",
        ".sh",
        ".bash",
        ".zsh",
        ".ps1",
        ".bat",
        ".cmd",
        ".sql",
        ".html",
        ".css",
        ".scss",
        ".lock",
        ".gitignore",
        ".gitattributes",
    }
    return suffix in file_suffixes


def parse_folder_name(repo_url: str) -> str:
    """
    Parses the repository URL to extract the folder name.

    Args:
        repo_url: The URL of the Git repository.

    Returns:
        The name of the folder where the repository will be cloned.
    """
    patterns = [
        r"github\.com/[^/]+/([^/]+)",
        r"gitlab[^/]+/[^/]+/([^/]+)",
        r"gitverse\.ru/[^/]+/([^/]+)",
        r"sourcecraft\.dev/[^/]+/([^/]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, repo_url)
        if match:
            folder_name = match.group(1)
            logger.debug(f"Parsed folder name '{folder_name}' from repo URL '{repo_url}'")
            return folder_name
    if os.path.exists(repo_url):
        folder_name = os.path.basename(repo_url)
        logger.debug(f"Parsed folder name '{folder_name}' from repo URL '{repo_url}'")
        return folder_name
    folder_name = re.sub(r"[:/]", "_", repo_url.rstrip("/"))
    logger.debug(f"Parsed folder name '{folder_name}' from repo URL '{repo_url}'")
    return folder_name


def osa_project_root() -> Path:
    """Returns osa_tool project root folder."""
    return Path(__file__).parent.parent


def build_arguments_path() -> str:
    """Returns arguments.yaml path for CLI parser."""
    return os.path.join(osa_project_root(), "config", "settings", "arguments.yaml")


def build_config_path() -> str:
    """Returns config.toml path for CLI parser and settings.py."""
    return os.path.join(osa_project_root(), "config", "settings", "config.toml")


def switch_to_output_directory(path: str | Path) -> Path:
    """
    Ensure the given output directory exists and change current working directory to it.
    Returns the resolved Path object.
    """
    output_path = Path(path).resolve()

    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {output_path}")

    os.chdir(output_path)
    logger.info(f"Output path changed to {output_path}")

    return output_path


def prepare_local_output_repository(source_repo: str | Path, output_dir: str | Path) -> Path:
    """
    Create or refresh a local working copy of the repository inside the output directory.

    This keeps local `-o/--output` runs consistent with remote processing, where OSA
    operates on a repository placed under the chosen output directory.
    """
    source_path = Path(source_repo).expanduser().resolve()
    output_root = Path(output_dir).expanduser().resolve()
    target_path = output_root / source_path.name

    try:
        source_path.relative_to(target_path)
    except ValueError:
        pass
    else:
        raise ValueError("The source repository is nested inside the target output repository path.")

    if target_path == source_path:
        logger.info("Local repository already points to the output path: %s", target_path)
        return target_path

    if output_root == source_path or output_root in source_path.parents:
        raise ValueError("The output directory cannot be the same as the source repository or located inside it.")

    if target_path.exists():
        logger.info("Refreshing local output repository at %s", target_path)
        _remove_tree(target_path)
    else:
        logger.info("Creating local output repository at %s", target_path)

    shutil.copytree(source_path, target_path)
    logger.info("Copied local repository from %s to %s", source_path, target_path)
    return target_path


def resolve_repo_path(repo_url: str | Path, base_dir: str | Path | None = None) -> Path:
    """
    Resolve the local filesystem path of the processed repository.

    For local processing, return the existing repository directory itself.
    For remote repositories, return the path where OSA clones the repository.
    """
    repo_candidate = Path(repo_url).expanduser()
    if repo_candidate.is_dir():
        resolved = repo_candidate.resolve()
        logger.debug(f"Resolved local repository path '{resolved}' from '{repo_url}'")
        return resolved

    root = Path(base_dir).resolve() if base_dir else Path.cwd()
    resolved = (root / parse_folder_name(str(repo_url))).resolve()
    logger.debug(f"Resolved cloned repository path '{resolved}' from '{repo_url}'")
    return resolved


def build_repo_browse_url(
    repo_url: str | Path,
    default_branch: str | None = None,
    relative_path: str | None = None,
    host: str | None = None,
    host_domain: str | None = None,
    full_name: str | None = None,
    clone_url_http: str | None = None,
) -> str:
    """
    Build a repository browse URL for remote repositories or a relative path for local ones.

    Local repositories return relative paths so generated markdown links stay usable offline.
    """
    relative_path = (relative_path or "").strip().replace("\\", "/").lstrip("/")

    resolved_host, resolved_host_domain, resolved_full_name = resolve_repo_web_identity(
        repo_url=repo_url,
        clone_url_http=clone_url_http,
        host=host,
        host_domain=host_domain,
        full_name=full_name,
    )

    if Path(repo_url).expanduser().is_dir() and not (resolved_host_domain and resolved_full_name):
        return relative_path or "."

    if not resolved_host_domain or not resolved_full_name:
        return relative_path or "."

    base_url = f"https://{resolved_host_domain}/{resolved_full_name}/"
    if not relative_path:
        return base_url

    if resolved_host == "sourcecraft":
        branch = default_branch or "main"
        return f"{base_url}browse/{relative_path}?rev={branch}"

    branch = default_branch or "main"
    browse_mode = "tree"
    if resolved_host in {"github", "gitlab"} and _looks_like_file_path(relative_path):
        browse_mode = "blob"

    return f"{base_url}{browse_mode}/{branch}/{relative_path}"


def resolve_repo_web_identity(
    repo_url: str | Path,
    clone_url_http: str | None = None,
    host: str | None = None,
    host_domain: str | None = None,
    full_name: str | None = None,
) -> tuple[str | None, str | None, str | None]:
    """
    Resolve repository web identity for link generation.

    Prefers explicit git settings, then falls back to the repository remote URL.
    """
    if host_domain and full_name:
        return host, host_domain, full_name

    candidate = clone_url_http or ""
    if candidate.endswith(".git"):
        candidate = candidate[:-4]

    if candidate.startswith(("http://", "https://")):
        try:
            inferred_host_domain, inferred_host, _, inferred_full_name = parse_git_url(candidate)
            return host or inferred_host, host_domain or inferred_host_domain, full_name or inferred_full_name
        except ValueError:
            logger.debug("Failed to infer repository web identity from clone URL '%s'", candidate)

    if not Path(repo_url).expanduser().is_dir() and isinstance(repo_url, str):
        try:
            inferred_host_domain, inferred_host, _, inferred_full_name = parse_git_url(repo_url)
            return host or inferred_host, host_domain or inferred_host_domain, full_name or inferred_full_name
        except ValueError:
            logger.debug("Failed to infer repository web identity from repo URL '%s'", repo_url)

    return host, host_domain, full_name


def get_base_repo_url(repo_url: str) -> str:
    """
    Extracts the base repository URL path from a given Git URL.

    Args:
        repo_url (str, optional): The Git repository URL. If not provided,
            the instance's `repo_url` attribute is used. Defaults to None.

    Returns:
        str: The base repository path (e.g., 'username/repo-name').

    Raises:
        ValueError: If the provided URL has unsupported format.
    """
    patterns = [
        r"https?://github\.com/([^/]+/[^/]+)",
        r"https?://[^/]*gitlab[^/]*/(.+)",
        r"https?://gitverse\.ru/([^/]+/[^/]+)",
        r"https?://sourcecraft\.dev/([^/]+/[^/]+)",
    ]
    for pattern in patterns:
        match = re.match(pattern, repo_url)
        if match:
            return match.group(1).rstrip("/")
    raise ValueError(f"Unsupported repository URL format: {repo_url}")


def delete_repository(repo_url: str) -> None:
    """
    Deletes the local directory of the downloaded repository based on its URL.
    Works reliably on Windows and Unix-like systems.

    Args:
        repo_url (str): The URL of the repository to be deleted.

    Raises:
        Exception: Logs an error message if deletion fails.
    """
    repo_path = resolve_repo_path(repo_url)

    try:
        if os.path.exists(repo_path):
            _remove_tree(repo_path)
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
        raise ValueError(f"Provided URL is not correct: {parsed_url.scheme}")

    if not parsed_url.netloc:
        raise ValueError(f"Invalid Git repository URL: {parsed_url}")

    host_domain = parsed_url.netloc
    host = host_domain.split(".")[0].lower()

    path_parts = [part for part in parsed_url.path.strip("/").split("/") if part]
    if len(path_parts) < 2:
        raise ValueError(f"Invalid Git repository URL path: {parsed_url.path}")

    if path_parts[-1].endswith(".git"):
        path_parts[-1] = path_parts[-1][:-4]

    full_name = "/".join(path_parts)
    name = path_parts[-1]

    return host_domain, host, name, full_name


def is_path(path_str: str) -> bool:
    if not path_str or not isinstance(path_str, str) or not path_str.strip():
        return False

    if re.match(r"^[a-zA-Z]+://", path_str):
        return False

    try:
        p = Path(path_str)

        if "\0" in path_str:
            return False
        _ = p.parts

        return True
    except (ValueError, TypeError, OSError):
        return False


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
        # Images
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".tiff",
        ".webp",
        ".drawio",
        ".svg",
        ".ico",
        # Videos
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".flv",
        ".wmv",
        ".webm",
        # Data files
        ".csv",
        ".tsv",
        ".parquet",
        ".json",
        ".xml",
        ".xls",
        ".xlsx",
        ".db",
        ".sqlite",
        ".npy",
        # Archives
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        # Binary / compiled artifacts
        ".exe",
        ".dll",
        ".so",
        ".bin",
        ".obj",
        ".class",
        ".pkl",
        ".dylib",
        ".o",
        ".a",
        ".lib",
        ".lo",
        ".mod",
        ".pyc",
        ".pyo",
        ".pyd",
        ".egg",
        ".whl",
        ".mat",
        # Documents
        ".pdf",
        ".doc",
        ".docx",
        ".odt",
        ".rtf",
        # Test or unused code artifacts
        ".gold",
        ".h",
        ".hpp",
        ".inl",
        ".S",
        # Temporary, system, and service files
        ".DS_Store",
        ".log",
        ".tmp",
        ".bak",
        ".swp",
        ".swo",
        # Project files (optional, depends on your context)
        ".csproj",
        ".sln",
        ".vcxproj",
        ".vcproj",
        ".dSYM",
        ".nb",
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
    it returns a empty string.

    Args:
        repo_path: Path to the repository being explored.

    Returns:
        str: The content of the README file or an empty string.
    """
    for file in ["README.md", "README_en.rst", "README.rst"]:
        readme_path = os.path.join(repo_path, file)

        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                return f.read()
    else:
        return ""


def detect_provider_from_url(url) -> str | None:
    """
    Detect the LLM provider from a given URL.

    Args:
        url (str): The API URL to analyze

    Returns:
        str: Detected provider name or 'None' if not recognized
    """
    if not url or not isinstance(url, str):
        return None

    providers = {
        "openai": [
            r".*openai\.com.*",
            r".*api\.openai\.com.*",
            r".*openrouter\.ai.*",
            r".*openrouter\.ai/api/v1.*",
            r".*vsegpt\.ru.*",
            r".*gigachat.*",
        ],
        "ollama": [r".*ollama\.com.*", r".*ollama.*", r"localhost.*:11434.*", r"\d*.*:11434.*"],
        "llama": [
            r".*llama.*",
            r".*llamacpp.*",
        ],
    }

    for provider, patterns in providers.items():
        for pattern in patterns:
            if re.search(pattern, url):
                logger.debug(f"Detected provider '{provider}' from URL '{url}'")
                return provider

    return None


def format_time(seconds: float) -> str:
    """Convert *seconds* into ``HH:MM:SS`` format."""
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def read_ipynb_file(file_path: str) -> str:
    """Extract code and markdown cells from a Jupyter notebook as plain text."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            notebook = json.load(f)
        lines: list[str] = []
        for cell in notebook.get("cells", []):
            cell_type = cell.get("cell_type")
            if cell_type in ("code", "markdown"):
                lines.append(f"# --- {cell_type.upper()} CELL ---")
                lines.extend(cell.get("source", []))
                lines.append("\n")
        return "\n".join(lines)
    except (OSError, json.JSONDecodeError):
        logger.error("Failed to read notebook: %s", file_path, exc_info=True)
        return ""


def read_file(file_path: str) -> str:
    """Read *file_path* and return its text content (empty string on failure).

    Handles Jupyter notebooks (``.ipynb``) specially and tries multiple encodings
    (utf-8, utf-16, latin-1) before giving up.
    """
    if file_path.endswith(".ipynb"):
        return read_ipynb_file(file_path)

    if not os.path.isfile(file_path):
        logger.warning("File not found: %s", file_path)
        return ""

    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue

    logger.error("Failed to read %s with any supported encoding", file_path)
    return ""
