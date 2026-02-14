import random
import string
from datetime import datetime, timedelta, timezone

from osa_tool.core.git.metadata import RepositoryMetadata


def random_string(length: int = 10) -> str:
    """Random string generator (letters + numbers)"""
    chars = string.ascii_lowercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def random_word() -> str:
    """Random word (letters only)"""
    return "".join(random.choice(string.ascii_lowercase) for _ in range(random.randint(3, 10)))


class DataFactory:
    """Universal data factory for tests"""

    @staticmethod
    def generate_git_settings(platform: str) -> dict:
        """Generating data for GitSettings (GitHub only)"""
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
        """Generating data for ModelSettings"""
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
        """Generating data for ModelGroupSettings"""
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
        """Generating data for WorkflowSettings"""
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
        """Generate a complete set of settings"""
        return {
            "git": self.generate_git_settings(platform),
            "llm": self.generate_model_group_settings(),
            "workflows": self.generate_workflow_settings(),
        }

    @staticmethod
    def random_source_rank_methods(force_overrides=None) -> dict:
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
