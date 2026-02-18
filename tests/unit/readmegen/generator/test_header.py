from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.generator.header import HeaderBuilder


@pytest.fixture
def header_builder(config_loader):
    """
    Builds a `HeaderBuilder` instance with mocked dependencies for testing purposes.
    
    Args:
        config_loader: The configuration loader used to initialize the `HeaderBuilder`.
    
    Yields:
        HeaderBuilder: An instance of `HeaderBuilder` that has been constructed with the provided
        `config_loader`. The instance is created within a context where several external
        dependencies (`SourceRank`, `load_data_metadata`, `PyPiPackageInspector`, and
        `DependencyExtractor`) are patched to return predefined mock objects. This allows
        tests to run in isolation without relying on the actual implementations of these
        components.
    """
    source_rank_mock = MagicMock()
    source_rank_mock.tree = {}

    metadata_mock = MagicMock()
    metadata_mock.license_name = "MIT"

    pypi_info_mock = MagicMock()
    pypi_info_mock.get_info.return_value = {
        "name": "TestPackage",
        "version": "1.0.0",
        "downloads": 1000,
    }

    dependency_extractor_mock = MagicMock()
    dependency_extractor_mock.extract_techs.return_value = ["Python", "Django"]

    with (
        patch(
            "osa_tool.readmegen.generator.header.SourceRank",
            return_value=source_rank_mock,
        ),
        patch(
            "osa_tool.readmegen.generator.header.load_data_metadata",
            return_value=metadata_mock,
        ),
        patch(
            "osa_tool.readmegen.generator.header.PyPiPackageInspector",
            return_value=pypi_info_mock,
        ),
        patch(
            "osa_tool.readmegen.generator.header.DependencyExtractor",
            return_value=dependency_extractor_mock,
        ),
    ):
        builder = HeaderBuilder(config_loader)
        yield builder


def test_load_template(header_builder):
    """
    Test that the header builder loads a template containing required sections.
    
    Args:
        header_builder: An instance of HeaderBuilder used to load the template.
    
    Returns:
        None
    
    This test verifies that the template returned by `load_template` contains the keys
    'headers', 'information_badges', and 'technology_badges'.
    """
    # Act
    template = header_builder.load_template()
    # Assert
    assert "headers" in template
    assert "information_badges" in template
    assert "technology_badges" in template


def test_generate_info_badges(header_builder):
    """
    Test that HeaderBuilder.generate_info_badges returns the expected badge strings.
    
    Parameters
    ----------
    header_builder
        An instance of HeaderBuilder used to generate the badges.
    
    Returns
    -------
    None
    
    This test verifies that the badges string returned by
    HeaderBuilder.generate_info_badges contains the expected PyPi and
    Downloads badge markdown links for the package 'TestPackage'.
    """
    # Act
    badges = header_builder.generate_info_badges()
    # Assert
    assert "[![PyPi](https://badge.fury.io/py/TestPackage.svg)](https://badge.fury.io/py/TestPackage)" in badges
    assert "[![Downloads](https://static.pepy.tech/badge/TestPackage)](https://pepy.tech/project/TestPackage)" in badges


def test_generate_license_badge(header_builder):
    """
    Test that the `generate_license_badge` method returns a badge string containing the expected license badge URL.
    
    Parameters
    ----------
    header_builder
        The HeaderBuilder instance used to generate the license badge.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the badge contains the expected URL.
    """
    # Act
    badge = header_builder.generate_license_badge()
    # Assert
    assert (
        "![License](https://img.shields.io/github/license/user/TestProject?style=flat&logo=opensourceinitiative&logoColor=white&color=blue)"
        in badge
    )


def test_build_header(header_builder):
    """
    Test that the header built by `header_builder` contains expected project name and PyPi badge.
    
    Args:
        header_builder: An instance of a header builder that provides a `build_header` method.
    
    Returns:
        None
    
    The test calls `build_header` and verifies that the resulting header string includes the
    project name "TestProject" and the PyPi badge marker "[![PyPi]". If either assertion
    fails, the test will raise an `AssertionError`.
    """
    # Act
    header = header_builder.build_header()
    # Assert
    assert "TestProject" in header
    assert "[![PyPi]" in header
