from io import BytesIO
from unittest.mock import mock_open, patch

import pytest

from osa_tool.readmegen.context.dependencies import DependencyExtractor

# Sample tree used in all tests
MOCK_TREE = """
requirements.txt
pyproject.toml
setup.py
"""
BASE_PATH = "/fake/repo"


@pytest.fixture
def extractor():
    return DependencyExtractor(tree=MOCK_TREE, base_path=BASE_PATH)


@patch("builtins.open", new_callable=mock_open, read_data="requests==2.25.1\nnumpy>=1.20.0\n")
@patch("osa_tool.readmegen.context.dependencies.find_in_repo_tree", return_value="requirements.txt")
def test_extract_from_requirements(mock_find, mock_file, extractor):
    # Act
    techs = extractor._extract_from_requirements()
    # Assert
    assert "requests" in techs
    assert "numpy" in techs


@patch("osa_tool.readmegen.context.dependencies.find_in_repo_tree", return_value="pyproject.toml")
@patch("builtins.open", new_callable=lambda: lambda f, mode="r", *args, **kwargs: BytesIO(b"""
[project]
dependencies = [
    "pandas >=1.0",
    "matplotlib"
]

[tool.poetry.dependencies]
python = ">=3.9"
scipy = "^1.8.0"
"""))
def test_extract_from_pyproject(mock_file, mock_find, extractor):
    # Act
    techs = extractor._extract_from_pyproject()
    # Assert
    assert "pandas" in techs
    assert "matplotlib" in techs
    assert "scipy" in techs


@patch("builtins.open", new_callable=mock_open, read_data="""
from setuptools import setup

setup(
    name="my_package",
    install_requires=[
        "flask",
        "sqlalchemy >=1.4",
        "gunicorn"
    ],
    python_requires=">=3.7"
)
""")
@patch("osa_tool.readmegen.context.dependencies.find_in_repo_tree", return_value="setup.py")
def test_extract_from_setup(mock_find, mock_file, extractor):
    # Act
    techs = extractor._extract_from_setup()
    # Assert
    assert "flask" in techs
    assert "sqlalchemy" in techs
    assert "gunicorn" in techs


@patch("osa_tool.readmegen.context.dependencies.DependencyExtractor._extract_from_requirements", return_value={"a"})
@patch("osa_tool.readmegen.context.dependencies.DependencyExtractor._extract_from_pyproject", return_value={"b"})
@patch("osa_tool.readmegen.context.dependencies.DependencyExtractor._extract_from_setup", return_value={"c"})
def test_extract_techs_combined(mock_setup, mock_pyproject, mock_req, extractor):
    # Act
    techs = extractor.extract_techs()
    # Assert
    assert techs == {"a", "b", "c"}
