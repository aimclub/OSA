from unittest.mock import patch

import pytest

from osa_tool.readmegen.generator.installation import InstallationSectionBuilder


def example_pypi_info():
    return {"name": "cool-package"}


@pytest.fixture
def patch_dependencies():
    with (
        patch("osa_tool.readmegen.generator.installation.load_data_metadata"),
        patch("osa_tool.readmegen.generator.installation.SourceRank") as mock_rank,
        patch("osa_tool.readmegen.generator.installation.PyPiPackageInspector") as mock_pypi,
        patch("osa_tool.readmegen.generator.installation.DependencyExtractor") as mock_dep,
    ):

        yield mock_rank, mock_pypi, mock_dep


@pytest.fixture
def builder_with_pypi(config_loader, patch_dependencies):
    _, mock_pypi, mock_dep = patch_dependencies
    mock_pypi.return_value.get_info.return_value = example_pypi_info()
    mock_dep.return_value.extract_python_version_requirement.return_value = "3.11"

    return InstallationSectionBuilder(config_loader)


@pytest.fixture
def builder_from_source_with_reqs(config_loader, patch_dependencies):
    mock_rank, mock_pypi, mock_dep = patch_dependencies
    mock_rank.return_value.tree = "requirements.txt"
    mock_pypi.return_value.get_info.return_value = None
    mock_dep.return_value.extract_python_version_requirement.return_value = None

    with patch(
        "osa_tool.readmegen.generator.installation.find_in_repo_tree",
        return_value="requirements.txt",
    ):
        return InstallationSectionBuilder(config_loader)


@pytest.fixture
def builder_from_source_without_reqs(config_loader, patch_dependencies):
    mock_rank, mock_pypi, mock_dep = patch_dependencies
    mock_rank.return_value.tree = "mock_tree"
    mock_pypi.return_value.get_info.return_value = None
    mock_dep.return_value.extract_python_version_requirement.return_value = "3.10"

    with patch("osa_tool.readmegen.generator.installation.find_in_repo_tree", return_value=None):
        return InstallationSectionBuilder(config_loader)


def test_build_with_pypi(builder_with_pypi):
    # Act
    result = builder_with_pypi.build_installation()
    # Assert
    assert "pip install cool-package" in result
    assert "requires Python 3.11" in result


def test_build_from_source_with_requirements(builder_from_source_with_reqs):
    # Act
    result = builder_from_source_with_reqs.build_installation()
    # Assert
    assert "git clone" in result
    assert "pip install -r requirements.txt" in result
    assert "requires Python" not in result


def test_build_from_source_without_requirements(builder_from_source_without_reqs):
    # Act
    result = builder_from_source_without_reqs.build_installation()
    # Assert
    assert "git clone" in result
    assert "pip install -r requirements.txt" not in result
    assert "requires Python 3.10" in result
