import json
import os

from osa_tool.operations.docs.community_docs_generation.codemeta_generator import (
    CodeMetaGenerator,
)


def test_codemeta_generator_basic(mock_config_manager, mock_repository_metadata, tmp_path):
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()
    git = mock_config_manager.config.git
    git.repository = str(repo_dir)

    mock_repository_metadata.name = "my-research-tool"
    mock_repository_metadata.description = "A great research tool"
    mock_repository_metadata.clone_url_http = "https://github.com/example/my-research-tool"
    mock_repository_metadata.license_name = "MIT"
    mock_repository_metadata.languages = ["Python", "C++"]
    mock_repository_metadata.created_at = "2024-01-01T00:00:00Z"
    mock_repository_metadata.pushed_at = "2024-06-01T00:00:00Z"
    mock_repository_metadata.updated_at = "2024-07-01T00:00:00Z"
    mock_repository_metadata.issues_url = "https://github.com/example/my-research-tool/issues"
    mock_repository_metadata.topics = ["machine-learning", "fair-software"]

    generator = CodeMetaGenerator(mock_config_manager, mock_repository_metadata)
    file_path = generator.generate()

    assert os.path.exists(file_path)
    assert file_path == str(repo_dir / "codemeta.json")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["@context"] == "https://w3id.org/codemeta/3.0"
    assert data["@type"] == "SoftwareSourceCode"
    assert data["name"] == "my-research-tool"
    assert data["description"] == "A great research tool"
    assert data["codeRepository"] == "https://github.com/example/my-research-tool"
    assert data["license"] == "https://spdx.org/licenses/MIT"
    assert data["programmingLanguage"] == ["Python", "C++"]
    assert data["dateCreated"] == "2024-01-01T00:00:00Z"
    assert data["dateModified"] == "2024-06-01T00:00:00Z"
    assert data["issueTracker"] == "https://github.com/example/my-research-tool/issues"
    assert data["keywords"] == ["machine-learning", "fair-software"]


def test_codemeta_generator_with_pyproject_pep621(mock_config_manager, mock_repository_metadata, tmp_path):
    repo_dir = tmp_path / "pep621_repo"
    repo_dir.mkdir()
    git = mock_config_manager.config.git
    git.repository = str(repo_dir)

    pyproject_content = """
[project]
name = "pep621-pkg"
version = "0.2.1"
description = "Description from pyproject"
license = { text = "Apache-2.0" }
authors = [
    { name = "Alice Smith", email = "alice@example.com" },
    { name = "Bob Jones" }
]
"""
    (repo_dir / "pyproject.toml").write_text(pyproject_content)

    mock_repository_metadata.name = "pep621-pkg"
    mock_repository_metadata.description = None
    mock_repository_metadata.license_name = None
    mock_repository_metadata.clone_url_http = "https://github.com/example/pep621-pkg"
    mock_repository_metadata.languages = ["Python"]
    mock_repository_metadata.created_at = None
    mock_repository_metadata.pushed_at = None
    mock_repository_metadata.updated_at = None
    mock_repository_metadata.issues_url = None
    mock_repository_metadata.topics = []

    generator = CodeMetaGenerator(mock_config_manager, mock_repository_metadata)
    file_path = generator.generate()

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["name"] == "pep621-pkg"
    assert data["description"] == "Description from pyproject"
    assert data["version"] == "0.2.1"
    assert data["license"] == "https://spdx.org/licenses/Apache-2.0"
    assert data["author"] == [
        {"@type": "Person", "name": "Alice Smith", "email": "alice@example.com"},
        {"@type": "Person", "name": "Bob Jones"},
    ]


def test_codemeta_generator_with_pyproject_poetry(mock_config_manager, mock_repository_metadata, tmp_path):
    repo_dir = tmp_path / "poetry_repo"
    repo_dir.mkdir()
    git = mock_config_manager.config.git
    git.repository = str(repo_dir)

    pyproject_content = """
[tool.poetry]
name = "poetry-pkg"
version = "1.5.0"
description = "Poetry package description"
license = "BSD-3-Clause"
authors = ["Charlie Brown <charlie@peanuts.com>", "Snoopy"]
"""
    (repo_dir / "pyproject.toml").write_text(pyproject_content)

    mock_repository_metadata.name = "poetry-pkg"
    mock_repository_metadata.description = None
    mock_repository_metadata.license_name = None
    mock_repository_metadata.clone_url_http = "https://github.com/example/poetry-pkg"
    mock_repository_metadata.languages = []
    mock_repository_metadata.created_at = None
    mock_repository_metadata.pushed_at = None
    mock_repository_metadata.updated_at = None
    mock_repository_metadata.issues_url = None
    mock_repository_metadata.topics = []

    generator = CodeMetaGenerator(mock_config_manager, mock_repository_metadata)
    file_path = generator.generate()

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["name"] == "poetry-pkg"
    assert data["description"] == "Poetry package description"
    assert data["version"] == "1.5.0"
    assert data["license"] == "https://spdx.org/licenses/BSD-3-Clause"
    assert data["author"] == [
        {"@type": "Person", "name": "Charlie Brown", "email": "charlie@peanuts.com"},
        {"@type": "Person", "name": "Snoopy"},
    ]
