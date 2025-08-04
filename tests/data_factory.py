import random
import string


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
    def generate_git_settings() -> dict:
        """Generating data for GitSettings (GitHub only)"""
        repo_name = random_word()
        user_name = random_word()
        return {
            "repository": f"https://github.com/{user_name}/{repo_name}",
            "full_name": f"{user_name}/{repo_name}",
            "host_domain": "github.com",
            "host": "github",
            "name": repo_name,
        }

    @staticmethod
    def generate_model_settings() -> dict:
        """Generating data for ModelSettings"""
        model_types = ["gpt", "claude", "llama"]
        version = random.choice(["3.5", "4.0", "4-turbo"])
        return {
            "api": "openai",
            "url": f"https://api.{random_word()}.com/v1",
            "context_window": random.randint(2048, 8192),
            "encoder": f"{random_word()}_encoder",
            "host_name": f"https://api.{random_word()}.com",
            "localhost": f"http://localhost:{random.randint(8000, 9000)}",
            "model": f"{random.choice(model_types)}-{version}",
            "path": f"/v1/{random_word()}",
            "temperature": round(random.uniform(0.1, 1.0), 1),
            "tokens": random.randint(512, 4096),
            "top_p": round(random.uniform(0.1, 1.0), 1),
        }

    @staticmethod
    def generate_workflow_settings() -> dict:
        """Generating data for WorkflowSettings"""
        return {
            "generate_workflows": random.choice([True, False]),
            "output_dir": f".github/{random_word()}",
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

    def generate_full_settings(self) -> dict:
        """Generate a complete set of settings"""
        return {
            "git": self.generate_git_settings(),
            "llm": self.generate_model_settings(),
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
