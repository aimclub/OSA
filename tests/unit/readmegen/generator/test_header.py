from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.generator.header import HeaderBuilder


@pytest.fixture
def header_builder(config_loader):
    source_rank_mock = MagicMock()
    source_rank_mock.tree = {}

    metadata_mock = MagicMock()
    metadata_mock.license_name = "MIT"

    pypi_info_mock = MagicMock()
    pypi_info_mock.get_info.return_value = {
        "name": "TestPackage",
        "version": "1.0.0",
        "downloads": 1000
    }

    dependency_extractor_mock = MagicMock()
    dependency_extractor_mock.extract_techs.return_value = ["Python", "Django"]

    with patch("osa_tool.readmegen.generator.header.SourceRank", return_value=source_rank_mock), \
         patch("osa_tool.readmegen.generator.header.load_data_metadata", return_value=metadata_mock), \
         patch("osa_tool.readmegen.generator.header.PyPiPackageInspector", return_value=pypi_info_mock), \
         patch("osa_tool.readmegen.generator.header.DependencyExtractor", return_value=dependency_extractor_mock):
        builder = HeaderBuilder(config_loader)
        yield builder


def test_load_template(header_builder):
    # Act
    template = header_builder.load_template()
    # Assert
    assert "headers" in template
    assert "information_badges" in template
    assert "technology_badges" in template


def test_generate_info_badges(header_builder):
    # Act
    badges = header_builder.generate_info_badges()
    # Assert
    assert "[![PyPi](https://badge.fury.io/py/TestPackage.svg)](https://badge.fury.io/py/TestPackage)" in badges
    assert "[![Downloads](https://static.pepy.tech/badge/TestPackage)](https://pepy.tech/project/TestPackage)" in badges


def test_generate_license_badge(header_builder):
    # Act
    badge = header_builder.generate_license_badge()
    # Assert
    assert "![License](https://img.shields.io/github/license/user/TestProject?style=flat&logo=opensourceinitiative&logoColor=white&color=blue)" in badge


def test_build_header(header_builder):
    # Act
    header = header_builder.build_header()
    # Assert
    assert "TestProject" in header
    assert "[![PyPi]" in header
