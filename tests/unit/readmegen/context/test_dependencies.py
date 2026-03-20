import textwrap

from osa_tool.tools.repository_analysis.dependencies import DependencyExtractor
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_extract_from_requirements(tmp_path):
    """
    Tests the extraction of technologies from a requirements.txt file.
    
    This test verifies that the DependencyExtractor correctly identifies technology names (e.g., "numpy", "pandas") from a requirements.txt file placed in a temporary directory. It ensures the extraction logic works for common dependency specification formats (>= and ==).
    
    Args:
        tmp_path: A temporary directory path fixture for creating test files.
    
    Returns:
        None
    """
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
    """
    Tests the extraction of dependencies from a pyproject.toml file using PEP 621 metadata.
    
    This test verifies that the DependencyExtractor correctly identifies dependencies listed under the `[project]` table in a pyproject.toml file, which follows the PEP 621 standard for project metadata.
    
    Args:
        tmp_path: A temporary directory path fixture for creating test files. The test writes a sample pyproject.toml file to this location to simulate a project environment.
    
    Returns:
        None
    """
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
    """
    Tests extraction of dependencies from a pyproject.toml file configured for Poetry.
    
    This test verifies that the DependencyExtractor correctly identifies dependencies and the Python version requirement from a Poetry-managed pyproject.toml file. It uses a temporary directory to create a mock pyproject.toml file, then checks that the extracted technologies include the expected dependencies and that the Python version requirement is accurately parsed.
    
    Args:
        tmp_path: A temporary directory path fixture used for test file creation.
    
    Returns:
        None
    """
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
    """
    Tests that DependencyExtractor correctly extracts dependencies from a setup.py file's install_requires field.
    
    This test ensures the extractor can parse and identify dependencies listed in the traditional setuptools install_requires list, which is a common pattern in Python projects.
    
    Args:
        tmp_path: A temporary directory path fixture for writing the test setup.py file.
    
    Returns:
        None
    """
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
    """
    Tests the behavior of DependencyExtractor when setup.py contains invalid Python syntax.
    
    This test verifies that the extractor gracefully handles a malformed setup.py file by returning empty results instead of raising an error. This ensures robustness when processing repositories with broken or non‑standard setup files.
    
    Args:
        tmp_path: Temporary directory path for creating test files.
    
    Steps performed:
        1. Creates a setup.py file with invalid Python syntax in the temporary directory.
        2. Initializes a DependencyExtractor with a mock repository tree that includes a setup.py.
        3. Calls extract_techs and extract_python_version_requirement on the extractor.
        4. Asserts that both methods return empty/default values (an empty set and None, respectively).
    
    Returns:
        None
    """
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
    """
    Tests the extraction of dependencies from an invalid pyproject.toml file.
    
    This test verifies that the DependencyExtractor correctly handles a malformed
    pyproject.toml file by returning empty results and logging an appropriate error.
    Specifically, it ensures that when pyproject.toml contains invalid TOML syntax,
    the extractor returns an empty set for technologies and None for the Python version,
    while logging a parsing or decoding failure message.
    
    Args:
        tmp_path: A temporary directory path fixture for creating test files.
        caplog: A fixture for capturing log messages.
    
    Returns:
        None
    """
    # Arrange
    (tmp_path / "pyproject.toml").write_text("invalid = {toml")

    # Act
    extractor = DependencyExtractor(get_mock_repo_tree("WITH_PYPROJECT"), str(tmp_path))

    # Assert
    assert extractor.extract_techs() == set()
    assert extractor.extract_python_version_requirement() is None
    assert "Failed to parse pyproject.toml" in caplog.text or "Failed to decode pyproject.toml" in caplog.text


def test_extract_from_requirements_different_encodings(tmp_path):
    """
    Tests extraction of dependencies from a requirements.txt file with different encodings.
    
    Creates a temporary requirements.txt file with UTF-16 encoding containing a dependency,
    then verifies that the DependencyExtractor correctly identifies the dependency.
    This ensures the extractor handles non-default file encodings correctly, which is important
    because dependency files in real projects may use various encodings.
    
    Args:
        tmp_path: A temporary directory path fixture for creating test files.
    """
    req_content = "scipy>=1.7\n"
    (tmp_path / "requirements.txt").write_text(req_content, encoding="utf-16")

    extractor = DependencyExtractor(get_mock_repo_tree("WITH_REQUIREMENTS_ONLY"), str(tmp_path))
    techs = extractor.extract_techs()
    assert "scipy" in techs


def test_no_dependency_files(tmp_path):
    """
    Tests that a repository with no dependency files yields empty results.
    
    This test ensures that when a repository contains no dependency files (e.g., pyproject.toml, setup.py, requirements.txt), the extractor correctly returns empty or None values for both technology extraction and Python version requirement detection.
    
    Args:
        tmp_path: Temporary directory path for test setup.
    
    Returns:
        None
    """
    # Arrange
    extractor = DependencyExtractor(get_mock_repo_tree("MINIMAL"), str(tmp_path))

    # Assert
    assert extractor.extract_techs() == set()
    assert extractor.extract_python_version_requirement() is None
