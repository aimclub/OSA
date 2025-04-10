"""Pytest fixtures for reuse across the test suite."""
import pytest
from osa_tool.utils import osa_project_root
from osa_tool.readmeai.config.settings import ConfigLoader
from osa_tool.readmeai.ingestion.models import (
    RepositoryContext,
    QuickStart,
    FileContext,
)

# -- readmeai.config -----------------


@pytest.fixture(scope="session")
def config_loader_fixture() -> ConfigLoader:
    config_dir = osa_project_root().joinpath('config/standart')
    return ConfigLoader(config_dir=str(config_dir))


# -- readmeai.ingestion --------------


@pytest.fixture(scope="session")
def repository_context_fixture() -> RepositoryContext:
    """
    Pytest fixture for the RepositoryContext model.
    """
    return RepositoryContext(
        files=[
            FileContext(
                path="requirements.txt",
                name="requirements.txt",
                ext="txt",
                content="pandas asyncio aiohttp aioresponses apache-flink "
                        "apache-kafka pandas pyflink",
                language="requirements.txt",
                dependencies=[
                    "pandas",
                    "asyncio",
                    "aiohttp",
                    "aioresponses",
                    "apache-flink",
                    "apache-kafka",
                    "pandas",
                    "pyflink",
                ],
            ),
            FileContext(
                path="setup.py",
                name="setup.py",
                ext="py",
                content='''""" setup.py """
from pathlib import Path
from setuptools import find_namespace_packages, setup

BASE_DIR = Path(__file__).parent

with open(Path(BASE_DIR, "requirements.txt"), "r") as file:
    required_packages = [ln.strip() for ln in file.readlines()]

docs_packages = ["mkdocs==1.3.0", "mkdocstrings==0.18.1"] style_packages = [
"black==22.3.0", "flake8==3.9.2", "isort==5.10.1"] test_packages = [
"pytest==7.1.2", "pytest-cov==2.10.1", "great-expectations==0.15.15"]

setup(
    name="STREAM-ON",
    version=0.1,
    description="",
    author="",
    author_email="",
    url="",
    python_requires=">=3.7",
    packages=find_namespace_packages(),
    install_requires=[required_packages],
    extras_require={
        "dev": docs_packages + style_packages + test_packages +
        ["pre-commit==2.19.0"],
        "test": test_packages,
    },
)
                ''',
                language="python",
                dependencies=[],
            ),
        ],
        dependencies=[
            "pip",
            "python",
            "conf.toml",
            "requirements.txt",
            "shell",
            "flink-config.yaml",
            "aiohttp",
            "pyflink",
            "apache-kafka",
            "asyncio",
            "pandas",
            "apache-flink",
            "aioresponses",
        ],
        languages=[
            "python",
            "conf.toml",
            "requirements.txt",
            "shell",
            "flink-config.yaml",
        ],
        language_counts={"txt": 1, "py": 4, "sh": 3, "yaml": 1, "toml": 1},
        metadata={
            "cicd": {},
            "containers": {},
            "documentation": {},
            "package_managers": {"pip": "requirements.txt"},
        },
        quickstart=QuickStart(
            primary_language="Python",
            language_counts={"txt": 1, "py": 4, "sh": 3, "yaml": 1, "toml": 1},
            package_managers={"pip": "requirements.txt"},
            containers={},
            install_commands="""**Using `pip`** &nbsp; [<img align="center" 
            src="https://img.shields.io/badge/Pip-3776AB.svg?style={
            badge_style}&logo=pypi&logoColor=white" />]( 
            https://pypi.org/project/pip/)

                ```sh
                ⨯ pip install -r requirements.txt
                ```
            """,
            usage_commands="""**Using `pip`** &nbsp; [<img align="center" 
            src="https://img.shields.io/badge/Pip-3776AB.svg?style={
            badge_style}&logo=pypi&logoColor=white" />]( 
            https://pypi.org/project/pip/)

                ```sh
                ⨯ python {entrypoint}
                ```
            """,
            test_commands="""**Using `pip`** &nbsp; [<img align="center" 
            src="https://img.shields.io/badge/Pip-3776AB.svg?style={
            badge_style}&logo=pypi&logoColor=white" />]( 
            https://pypi.org/project/pip/)

                ```sh
                ⨯ pytest
                ```
            """,
        ),
        docs_paths=["docs", "examples"]
    )
