import random
import string
from datetime import datetime, timedelta, timezone

from osa_tool.core.git.metadata import RepositoryMetadata


def random_string(length: int = 10) -> str:
    """
    Generate a random string composed of lowercase letters and digits.
    
    This utility function creates a string of a specified length by randomly selecting
    characters from the combined set of lowercase ASCII letters and digits. It is
    commonly used for generating identifiers, temporary filenames, or test data where
    a simple, random alphanumeric string is needed.
    
    Args:
        length: The desired length of the random string. Defaults to 10.
    
    Returns:
        A random string containing only lowercase letters and digits.
    """
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def random_word() -> str:
    """
    Generate a random word consisting only of lowercase letters.
    
    The word length is randomly chosen between 3 and 10 characters, inclusive.
    This method is typically used to create placeholder text or identifiers for testing and demonstration purposes.
    
    Returns:
        A random lowercase alphabetic string.
    """
    return "".join(random.choice(string.ascii_lowercase) for _ in range(random.randint(3, 10)))


class DataFactory:
    """
    Universal data factory for tests
    """


    @staticmethod
    def generate_git_settings(platform: str) -> dict:
        """
        Generate a mock Git settings dictionary for a specified platform.
        
        This method creates a structured set of placeholder Git repository details,
        primarily for testing, demonstration, or data seeding purposes within the OSA Tool.
        It currently supports generating data for platforms like GitHub and Gitverse by
        constructing realistic URLs and identifiers using random words.
        
        Args:
            platform: The name of the Git hosting platform (e.g., 'github', 'gitverse').
                      Determines the domain suffix (.com for most platforms, .ru for 'gitverse').
        
        Returns:
            A dictionary containing the following keys:
                - repository: The full HTTPS URL to the mock repository.
                - full_name: The repository path in 'user_name/repo_name' format.
                - host_domain: The domain of the Git hosting platform.
                - host: The platform name as provided.
                - name: The generated repository name.
        """
        repo_name = random_word()
        user_name = random_word()
        platform_domain = f"{platform}.com" if platform != "gitverse" else f"{platform}.ru"

        return {
            "repository": f"https://{platform_domain}/{user_name}/{repo_name}",
            "full_name": f"{user_name}/{repo_name}",
            "host_domain": f"{platform_domain}",
            "host": platform,
            "name": repo_name,
        }

    @staticmethod
    def generate_model_settings() -> dict:
        """
        Generate a random dictionary representing model settings for testing or demonstration.
        
        This static method creates a dictionary with randomized values that mimic configuration
        parameters for a language model API client. It is used to produce placeholder data
        for testing scenarios where realistic but non-sensitive model settings are needed.
        
        Returns:
            A dictionary containing randomized keys and values typical of model configuration,
            such as API details, rate limits, URLs, model specifications, and generation parameters.
        """
        model_types = ["gpt", "claude", "llama"]
        version = random.choice(["3.5", "4.0", "4-turbo"])
        return {
            "api": "openai",
            "rate_limit": random.randint(5, 20),
            "base_url": f"https://api.openai.{random_word()}.com/v1",
            "encoder": f"{random_word()}_encoder",
            "host_name": f"https://api.{random_word()}.com",
            "localhost": f"http://localhost:{random.randint(8000, 9000)}",
            "model": f"{random.choice(model_types)}-{version}",
            "path": f"/v1/{random_word()}",
            "temperature": round(random.uniform(0.1, 1.0), 1),
            "max_tokens": random.randint(512, 4096),
            "context_window": random.randint(8192, 16385),
            "top_p": round(random.uniform(0.1, 1.0), 1),
            "max_retries": random.randint(3, 10),
            "system_prompt": random_word(),
            "allowed_providers": random.sample(["google-vertex", "azure"], k=1),
            "fallback_models": random.sample(["gpt-oss-120b", "claude-haiku-4.5"], k=1),
        }

    @staticmethod
    def generate_model_group_settings() -> dict:
        """
        Generate a dictionary of model group settings for different operational tasks.
        
        This static method creates a set of model configuration dictionaries, each intended for a specific use case within the OSA Tool's pipeline. It provides consistent, randomized model settings across various tasks—such as documentation generation, validation, and general operations—ensuring that each task has its own isolated copy of settings. This isolation prevents unintended side-effects from modifications and supports task-specific customization if needed in the future.
        
        The method starts by generating a base set of randomized model settings via `DataFactory.generate_model_settings`. It then returns a dictionary where each key represents a distinct task group, and each value is a copy of those base settings. All groups initially receive identical settings, but they are independent copies to allow for safe, independent adjustments per task.
        
        Returns:
            A dictionary with keys naming different task groups (e.g., "default", "for_docstring_gen", "for_readme_gen", "for_validation", "for_general_tasks"). Each value is a separate copy of the randomized model settings dictionary.
        """
        default_settings = DataFactory.generate_model_settings()

        # Создаем настройки для разных задач (могут быть такими же или отличаться)
        return {
            "default": default_settings,
            "for_docstring_gen": default_settings.copy(),
            "for_readme_gen": default_settings.copy(),
            "for_validation": default_settings.copy(),
            "for_general_tasks": default_settings.copy(),
        }

    @staticmethod
    def generate_workflow_settings() -> dict:
        """
        Generates random workflow configuration data for testing or simulation purposes.
        
        This method creates a dictionary containing randomized settings typically used in
        CI/CD workflow configurations. Each key represents a workflow option with a
        randomly selected value (boolean, list, or string) to simulate various possible
        configurations.
        
        Returns:
            A dictionary with randomized workflow settings including:
            - generate_workflows: Whether to generate workflows
            - include_tests: Whether to include test steps
            - include_black: Whether to include Black formatting
            - include_pep8: Whether to include PEP8 checks
            - include_autopep8: Whether to include autopep8 formatting
            - include_fix_pep8: Whether to include PEP8 fixing
            - include_pypi: Whether to include PyPI deployment
            - python_versions: Two randomly selected Python versions
            - pep8_tool: Randomly selected PEP8 tool (flake8 or pylint)
            - use_poetry: Whether to use Poetry for dependency management
            - branches: Two randomly selected branch names
            - codecov_token: Whether to include a Codecov token
            - include_codecov: Whether to include Codecov integration
        """
        return {
            "generate_workflows": random.choice([True, False]),
            "include_tests": random.choice([True, False]),
            "include_black": random.choice([True, False]),
            "include_pep8": random.choice([True, False]),
            "include_autopep8": random.choice([True, False]),
            "include_fix_pep8": random.choice([True, False]),
            "include_pypi": random.choice([True, False]),
            "python_versions": random.sample(["3.8", "3.9", "3.10", "3.11"], k=2),
            "pep8_tool": random.choice(["flake8", "pylint"]),
            "use_poetry": random.choice([True, False]),
            "branches": random.sample(["main", "master", "dev"], k=2),
            "codecov_token": random.choice([True, False]),
            "include_codecov": random.choice([True, False]),
        }

    def generate_full_settings(self, platform: str = "github") -> dict:
        """
        Generate a complete set of settings for the OSA Tool.
        
        This method consolidates configuration settings from multiple specialized generators into a single dictionary. It is used to provide a unified configuration object that encompasses all necessary settings for the tool's documentation and repository enhancement pipeline.
        
        Args:
            platform: The version control platform for which to generate Git-related settings. Defaults to "github".
        
        Returns:
            A dictionary containing three key groups of settings:
                - "git": Settings for Git operations and platform-specific configurations.
                - "llm": Settings for language model configurations and parameters.
                - "workflows": Settings for defining and controlling automated workflows.
        """
        return {
            "git": self.generate_git_settings(platform),
            "llm": self.generate_model_group_settings(),
            "workflows": self.generate_workflow_settings(),
        }

    @staticmethod
    def random_source_rank_methods(force_overrides=None) -> dict:
        """
        Generates a dictionary of boolean flags for various source code ranking criteria, optionally overridden by provided values.
        This is used to randomly enable or disable specific ranking methods during data generation or testing, allowing for varied simulation scenarios.
        
        Args:
            force_overrides: A dictionary containing manual overrides for specific ranking methods. Keys should be method names from the predefined list. If a method is not present in this dictionary, a random boolean value (True or False) is assigned.
        
        Returns:
            dict: A dictionary where keys are ranking method names (e.g., 'readme_presence', 'license_presence') and values are booleans indicating whether the criteria should be considered. The method list includes: 'readme_presence', 'license_presence', 'examples_presence', 'docs_presence', 'tests_presence', 'citation_presence', 'contributing_presence', and 'requirements_presence'.
        """
        methods = [
            "readme_presence",
            "license_presence",
            "examples_presence",
            "docs_presence",
            "tests_presence",
            "citation_presence",
            "contributing_presence",
            "requirements_presence",
        ]
        return {method: force_overrides.get(method, random.choice([True, False])) for method in methods}

    @staticmethod
    def generate_repository_metadata_raw(platform: str, owner: str, repo_name: str, repo_url: str) -> dict:
        """
        Generates a dictionary containing simulated raw repository metadata.
        
        This method constructs a comprehensive metadata object with randomized values for various repository attributes such as star counts, descriptions, dates, and URLs. The structure and date formatting are adjusted based on the specified hosting platform. This is used to create realistic, fake data for testing or demonstration purposes without querying actual APIs.
        
        Args:
            platform: The hosting service for the repository (e.g., 'github', 'gitlab', 'gitverse'). Determines date format and certain field defaults (e.g., watchers_count is zero for GitLab, has_projects defaults to True for GitLab).
            owner: The username or organization name that owns the repository.
            repo_name: The name of the repository.
            repo_url: The base URL of the repository. Used to derive clone_url and other resource URLs.
        
        Returns:
            dict: A dictionary containing detailed repository metadata including owner information, statistics, timestamps, and resource URLs. Key fields include name, full_name, owner, description, stargazers_count, forks_count, watchers_count, open_issues_count, default_branch, created_at, updated_at, pushed_at, size, clone_url, ssh_url, contributors_url, languages_url, issues_url, language, languages, topics, has_wiki, has_issues, has_projects, private, homepage, and license. For GitLab, an additional path_with_namespace field is included.
        """
        now = datetime.now(timezone.utc)
        random_date = lambda offset=0: (now - timedelta(days=random.randint(offset, offset + 1000)))

        if platform == "gitlab":
            format_date = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%S")
            created_at = format_date(random_date(1000))
            updated_at = format_date(random_date(100))
            pushed_at = format_date(random_date(10))
        else:
            format_date = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")
            created_at = format_date(random_date(1000))
            updated_at = format_date(random_date(100))
            pushed_at = format_date(random_date(10))

        base_domain = {"github": "github.com", "gitlab": "gitlab.com", "gitverse": "gitverse.ru"}.get(
            platform, "github.com"
        )

        metadata = {
            "name": repo_name,
            "full_name": f"{owner}/{repo_name}",
            "owner": {"login": owner, "html_url": f"https://{base_domain}/{owner}"},
            "description": " ".join([random_word() for _ in range(random.randint(5, 15))]),
            "stargazers_count": random.randint(0, 1000),
            "forks_count": random.randint(0, 500),
            "watchers_count": random.randint(0, 100) if platform != "gitlab" else 0,
            "open_issues_count": random.randint(0, 100),
            "default_branch": random.choice(["main", "master", "dev"]),
            "created_at": created_at,
            "updated_at": updated_at,
            "pushed_at": pushed_at,
            "size": random.randint(10, 50000),
            "clone_url": f"{repo_url}.git",
            "ssh_url": f"git@{base_domain}:{owner}/{repo_name}.git",
            "contributors_url": f"https://{base_domain}/{owner}/{repo_name}/contributors",
            "languages_url": f"https://{base_domain}/{owner}/{repo_name}/languages",
            "issues_url": f"https://{base_domain}/{owner}/{repo_name}/issues",
            "language": random.choice(["Python", "JavaScript", "Go", "Rust", "C++", None]),
            "languages": {
                lang: random.randint(1000, 50000)
                for lang in random.sample(["Python", "JavaScript", "Go", "Rust", "C++"], k=random.randint(1, 3))
            },
            "topics": random.sample(["ai", "ml", "opensource", "backend", "frontend", "cli"], k=random.randint(0, 5)),
            "has_wiki": random.choice([True, False]),
            "has_issues": random.choice([True, False]),
            "has_projects": random.choice([True, False]) if platform != "gitlab" else True,
            "private": random.choice([True, False]),
            "homepage": f"https://{random_word()}.com",
            "license": (
                {
                    "name": random.choice(["MIT", "GPLv3", "Apache 2.0", "BSD"]),
                    "url": f"https://opensource.org/licenses/{random_word()}",
                }
                if random.random() > 0.5
                else None
            ),
        }

        if platform == "gitlab":
            metadata["path_with_namespace"] = f"{owner}/{repo_name}"

        return metadata

    def generate_repository_metadata(
        self, platform: str, owner: str, repo_name: str, repo_url: str
    ) -> RepositoryMetadata:
        """
        Generates structured metadata for a specific repository by fetching and parsing raw platform data.
        
        This method serves as a wrapper that transforms raw platform API data into a structured RepositoryMetadata object. It centralizes the extraction of key repository attributes—such as statistics, URLs, timestamps, and configuration flags—into a consistent format for downstream use.
        
        Args:
            platform: The hosting service where the repository is located (e.g., GitHub).
            owner: The username or organization that owns the repository.
            repo_name: The name of the repository.
            repo_url: The full URL of the repository.
        
        Returns:
            RepositoryMetadata: An object containing detailed repository information. The returned fields include name, full_name, owner details, description, counts (stars, forks, watchers, open issues), default branch, timestamps (created_at, updated_at, pushed_at), size in KB, clone URLs (HTTP and SSH), API URLs (contributors, languages, issues), primary language, list of languages, topics, boolean flags (has_wiki, has_issues, has_projects, is_private), homepage URL, and license information (name and URL, if available).
        
        Note:
            The method internally calls `generate_repository_metadata_raw` to obtain the raw data dictionary, then maps its keys to the corresponding attributes of the RepositoryMetadata object. This abstraction ensures that consumers receive a clean, typed object instead of raw dictionary data.
        """
        raw = self.generate_repository_metadata_raw(platform, owner, repo_name, repo_url)

        return RepositoryMetadata(
            name=raw["name"],
            full_name=raw["full_name"],
            owner=raw["owner"]["login"],
            owner_url=raw["owner"]["html_url"],
            description=raw["description"],
            stars_count=raw["stargazers_count"],
            forks_count=raw["forks_count"],
            watchers_count=raw["watchers_count"],
            open_issues_count=raw["open_issues_count"],
            default_branch=raw["default_branch"],
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
            pushed_at=raw["pushed_at"],
            size_kb=raw["size"],
            clone_url_http=raw["clone_url"],
            clone_url_ssh=raw["ssh_url"],
            contributors_url=raw["contributors_url"],
            languages_url=raw["languages_url"],
            issues_url=raw["issues_url"],
            language=raw["language"],
            languages=list(raw["languages"].keys()),
            topics=raw["topics"],
            has_wiki=raw["has_wiki"],
            has_issues=raw["has_issues"],
            has_projects=raw["has_projects"],
            is_private=raw["private"],
            homepage_url=raw["homepage"],
            license_name=raw["license"]["name"] if raw["license"] else None,
            license_url=raw["license"]["url"] if raw["license"] else None,
        )
