import textwrap

from osa_tool.tools.repository_analysis.dependencies import DependencyExtractor
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_extract_from_requirements(tmp_path):
    # Arrange
    require = textwrap.dedent("""
        numpy>=1.21
        pandas==1.5.0
        """)
    (tmp_path / "requirements.txt").write_text(require)
    extractor = DependencyExtractor(get_mock_repo_tree("WITH_REQUIREMENTS_ONLY"), str(tmp_path))

    # Act
    techs = extractor.extract_techs()

    # Assert
    assert {"numpy", "pandas"} <= techs


def test_extract_from_pyproject_pep621(tmp_path):
    # Arrange
    pyproj = textwrap.dedent("""
        [project]
        dependencies = [
            "flask>=2.0",
            "requests"
        ]
        requires-python = ">=3.9"
        """)
    (tmp_path / "pyproject.toml").write_text(pyproj)

    extractor = DependencyExtractor(get_mock_repo_tree("WITH_PYPROJECT"), str(tmp_path))

    # Act
    techs = extractor.extract_techs()

    # Assert
    assert {"flask>=2.0", "requests"} <= techs


def test_extract_from_pyproject_poetry(tmp_path):
    # Arrange
    pyproj = textwrap.dedent("""
        [tool.poetry.dependencies]
        python = ">=3.8"
        torch = "^1.12"
        transformers = "^4.21"
        """)
    (tmp_path / "pyproject.toml").write_text(pyproj)

    extractor = DependencyExtractor(get_mock_repo_tree("WITH_PYPROJECT"), str(tmp_path))

    # Act
    techs = extractor.extract_techs()
    python_req = extractor.extract_python_version_requirement()

    # Assert
    assert {"torch", "transformers", "python"} <= techs
    assert python_req == ">=3.8"


def test_extract_from_setup_install_requires(tmp_path):
    # Arrange
    setup_code = textwrap.dedent("""
        from setuptools import setup

        setup(
            name="demo",
            install_requires=[
                "Django>=3.2",
                "sqlalchemy==1.4.0",
            ],
            python_requires=">=3.7",
        )
        """)
    (tmp_path / "setup.py").write_text(setup_code, encoding="utf-8")

    extractor = DependencyExtractor(get_mock_repo_tree("WITH_SETUP"), str(tmp_path))

    # Act
    techs = extractor.extract_techs()

    # Assert
    assert {"django>=3.2", "sqlalchemy==1.4.0"} <= techs


def test_extract_from_setup_invalid_syntax(tmp_path):
    # Arrange
    setup_file = tmp_path / "setup.py"
    setup_file.write_text("this is not valid python", encoding="utf-8")

    extractor = DependencyExtractor(get_mock_repo_tree("WITH_SETUP"), str(tmp_path))

    # Act
    techs = extractor.extract_techs()
    python_version = extractor.extract_python_version_requirement()

    # Assert
    assert techs == set()
    assert python_version is None


def test_extract_from_pyproject_toml_invalid(tmp_path, caplog):
    # Arrange
    (tmp_path / "pyproject.toml").write_text("invalid = {toml")

    # Act
    extractor = DependencyExtractor(get_mock_repo_tree("WITH_PYPROJECT"), str(tmp_path))

    # Assert
    assert extractor.extract_techs() == set()
    assert extractor.extract_python_version_requirement() is None
    assert "Failed to parse pyproject.toml" in caplog.text or "Failed to decode pyproject.toml" in caplog.text


def test_extract_from_requirements_different_encodings(tmp_path):
    req_content = "scipy>=1.7\n"
    (tmp_path / "requirements.txt").write_text(req_content, encoding="utf-16")

    extractor = DependencyExtractor(get_mock_repo_tree("WITH_REQUIREMENTS_ONLY"), str(tmp_path))
    techs = extractor.extract_techs()
    assert "scipy" in techs


def test_no_dependency_files(tmp_path):
    # Arrange
    extractor = DependencyExtractor(get_mock_repo_tree("MINIMAL"), str(tmp_path))

    # Assert
    assert extractor.extract_techs() == set()
    assert extractor.extract_python_version_requirement() is None
