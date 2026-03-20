import os
import re
import shutil
import stat
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console

from osa_tool.utils.logger import logger

console = Console()


def rich_section(title: str):
    """
    Print a styled section header in the console to visually separate log sections.
    
    This method uses the Rich library to print a blank line followed by a horizontal rule with the given title, styled in bold cyan. This visual separation helps organize console output into distinct, readable sections, which is especially useful in automated documentation and analysis pipelines where clear logging is important.
    
    Args:
        title: Title text for the section header.
    """
    console.print("")
    console.rule(f"[bold cyan]{title}[/bold cyan]", style="cyan")


def parse_folder_name(repo_url: str) -> str:
    """
    Parses the repository URL to extract the folder name for cloning.
    
    The method first attempts to match common Git hosting URL patterns (GitHub, GitLab, Gitverse) to extract the repository name. If no pattern matches, it falls back to replacing URL separators (':' and '/') with underscores to create a safe folder name.
    
    Args:
        repo_url: The URL of the Git repository.
    
    Returns:
        The name of the folder where the repository will be cloned.
    """
    patterns = [r"github\.com/[^/]+/([^/]+)", r"gitlab[^/]+/[^/]+/([^/]+)", r"gitverse\.ru/[^/]+/([^/]+)"]
    for pattern in patterns:
        match = re.search(pattern, repo_url)
        if match:
            folder_name = match.group(1)
            logger.debug(f"Parsed folder name '{folder_name}' from repo URL '{repo_url}'")
            return folder_name
    folder_name = re.sub(r"[:/]", "_", repo_url.rstrip("/"))
    logger.debug(f"Parsed folder name '{folder_name}' from repo URL '{repo_url}'")
    return folder_name


def osa_project_root() -> Path:
    """
    Returns the absolute path to the root directory of the osa_tool project.
    
    This method determines the project root by navigating two levels up from the current file's location. It is used to provide a consistent base path for accessing project resources, configuration files, or other directories relative to the project root.
    
    Returns:
        The Path object representing the osa_tool project root folder.
    """
    return Path(__file__).parent.parent


def build_arguments_path() -> str:
    """
    Returns the absolute file path to the arguments.yaml configuration file used by the CLI parser.
    
    This method constructs the path by joining the project root directory with the relative path to the configuration file. It ensures the CLI parser can reliably locate its argument definitions.
    
    Returns:
        The full path to the arguments.yaml file.
    """
    return os.path.join(osa_project_root(), "config", "settings", "arguments.yaml")


def build_config_path() -> str:
    """
    Returns the absolute path to the config.toml file used by the CLI parser and settings.py.
    
    This method constructs the path by joining the osa_tool project root directory with the relative path to the configuration file. It ensures that the configuration file is consistently located relative to the project root, which is necessary for the CLI and settings modules to access shared configuration.
    
    Returns:
        The absolute path string to the config.toml configuration file.
    """
    return os.path.join(osa_project_root(), "config", "settings", "config.toml")


def switch_to_output_directory(path: str | Path) -> Path:
    """
    Ensure the given output directory exists and change current working directory to it.
    Returns the resolved Path object.
    
    This method is used to set up a working environment for output operations by guaranteeing the target directory is available and making it the current working directory. Changing the directory simplifies subsequent file operations, as relative paths will be resolved relative to this output location.
    
    Args:
        path: The output directory path (as a string or Path object). If the directory does not exist, it will be created, including any necessary parent directories.
    
    Returns:
        The resolved Path object representing the absolute output directory.
    """
    output_path = Path(path).resolve()

    if not output_path.exists():
        output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {output_path}")

    os.chdir(output_path)
    logger.info(f"Output path changed to {output_path}")

    return output_path


def get_base_repo_url(repo_url: str) -> str:
    """
    Extracts the base repository URL path from a given Git URL.
    
    Args:
        repo_url: The Git repository URL to parse. Must be provided; there is no default or instance attribute fallback.
    
    Returns:
        The base repository path (e.g., 'username/repo-name').
    
    Raises:
        ValueError: If the provided URL does not match any of the supported Git hosting patterns.
    
    Why:
        This method standardizes repository URLs by extracting the unique identifier (owner and repository name) from various Git hosting services. It enables consistent handling of repository references across different platforms (GitHub, GitLab, GitVerse) by isolating the common path component.
    """
    patterns = [
        r"https?://github\.com/([^/]+/[^/]+)",
        r"https?://[^/]*gitlab[^/]*/(.+)",
        r"https?://gitverse\.ru/([^/]+/[^/]+)",
    ]
    for pattern in patterns:
        match = re.match(pattern, repo_url)
        if match:
            return match.group(1).rstrip("/")
    raise ValueError(f"Unsupported repository URL format: {repo_url}")


def delete_repository(repo_url: str) -> None:
    """
    Deletes the local directory of the downloaded repository based on its URL.
    Works reliably on Windows and Unix-like systems by forcibly removing read-only files if necessary.
    
    Args:
        repo_url: The URL of the repository to be deleted. The local directory name is derived from this URL.
    
    Raises:
        Exception: Logs an error message if deletion fails. The method logs both success and failure outcomes, and does nothing if the directory does not exist.
    
    Why:
        This method ensures that temporary or downloaded repository directories are cleaned up after use, preventing leftover files from consuming disk space. The force-removal of read-only files handles permission issues that can occur on some systems.
    """
    repo_path = os.path.join(os.getcwd(), parse_folder_name(repo_url))

    def on_rm_error(func, path, exc_info):
        """Force-remove read-only files and log the issue."""
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            logger.error(f"Failed to forcibly remove {path}: {e}")

    try:
        if os.path.exists(repo_path):
            shutil.rmtree(repo_path, onerror=on_rm_error)
            logger.info(f"Directory {repo_path} has been deleted.")
        else:
            logger.info(f"Directory {repo_path} does not exist.")
    except Exception as e:
        logger.error(f"Failed to delete directory {repo_path}: {e}")


def parse_git_url(repo_url: str) -> tuple[str, str, str, str]:
    """
    Parse a Git repository URL and extract its components.
    
    Args:
        repo_url: The URL of the Git repository (must be an http or https URL).
    
    Returns:
        tuple: A four-element tuple containing:
            - host_domain: The full network location (e.g., "github.com").
            - host: The first part of the domain, typically the platform name (e.g., "github").
            - name: The final segment of the URL path, representing the project/repository name.
            - full_name: The combination of the first two path segments, usually "owner/repository".
    
    Raises:
        ValueError: If the URL scheme is not http/https or if the network location is missing.
    """
    parsed_url = urlparse(repo_url)

    if parsed_url.scheme not in ["http", "https"]:
        raise ValueError(f"Provided URL is not correct: {parsed_url.scheme}")

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
    Builds a text representation of the project file tree, excluding the .git directory and other non‑source files.
    
    The tree includes relative paths of files and directories, each on a new line. It intentionally filters out:
    - The `.git` directory and any paths containing “log” or “logs” (to avoid version‑control and log clutter).
    - A predefined set of file extensions (images, videos, archives, binaries, documents, temporary files, etc.) that are typically not needed for source‑code analysis.
    
    Args:
        repo_path: Path to the repository being explored.
    
    Returns:
        str: A text representation of the repository's file tree with relative paths to files and directories,
             excluding the `.git` directory and filtered extensions. Each file or directory path is on a new line.
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
    
    It checks for the presence of common README filenames in order: "README.md", "README_en.rst", and "README.rst". The first file found is read and its content returned. This prioritization ensures that a Markdown README is preferred over reStructuredText, and an English version is preferred over a generic .rst file. If none of these files exist, a default message is returned.
    
    WHY: The method supports multiple common README naming conventions and formats to maximize compatibility across open-source repositories, increasing the chance of successfully extracting documentation.
    
    Args:
        repo_path: Path to the repository directory to search.
    
    Returns:
        str: The UTF-8 decoded content of the first README file found, or the string "No README.md file" if no matching file is present.
    """
    for file in ["README.md", "README_en.rst", "README.rst"]:
        readme_path = os.path.join(repo_path, file)

        if os.path.exists(readme_path):
            with open(readme_path, "r", encoding="utf-8") as f:
                return f.read()
    else:
        return "No README.md file"


def detect_provider_from_url(url) -> str | None:
    """
    Detect the LLM provider from a given URL by matching against known provider URL patterns.
    
    This is used to automatically determine the appropriate provider context for API interactions, enabling the tool to adapt its behavior or configuration based on the service being called.
    
    Args:
        url: The API URL to analyze. If the input is not a string or is empty, the function returns None.
    
    Returns:
        The detected provider name as a string (e.g., 'openai', 'ollama', 'llama'). Returns None if no known provider pattern matches the URL.
    
    Note:
        The detection relies on regular expression patterns defined for each provider. Patterns include common domains, local endpoints, and alternative service URLs (e.g., OpenRouter, GigaChat for OpenAI; local Ollama instances).
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
