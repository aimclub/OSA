import json

import pytest

from osa_tool.readmegen.generator.builder_article import MarkdownBuilderArticle


def example_overview():
    return json.dumps({"overview": "This is the overview section."})


def example_content():
    return json.dumps({"content": "This is the content section."})


def example_algorithms():
    return json.dumps({"algorithms": "This is the algorithms section."})


@pytest.fixture
def markdown_builder(config_loader, mock_load_data_metadata):
    return MarkdownBuilderArticle(
        config_loader=config_loader,
        overview=example_overview(),
        content=example_content(),
        algorithms=example_algorithms(),
    )


def test_load_template(markdown_builder):
    # Act
    template = markdown_builder.load_template()
    # Assert
    assert "headers" in template
    assert "overview" in template


def test_header_section(markdown_builder):
    # Act
    header = markdown_builder.header
    # Assert
    assert "TestProject" in header


def test_overview_section(markdown_builder):
    # Act
    section = markdown_builder.overview
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Overview")
    assert "This is the overview section." in section


def test_content_section(markdown_builder):
    # Act
    section = markdown_builder.content
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Repository content")
    assert "This is the content section." in section


def test_algorithms_section(markdown_builder):
    # Act
    section = markdown_builder.algorithms
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Used algorithms")
    assert "This is the algorithms section." in section


def test_build_readme(markdown_builder):
    # Act
    readme = markdown_builder.build()
    # Assert
    assert isinstance(readme, str)
    assert "## Overview" in readme
    assert "## Repository content" in readme
    assert "## Used algorithms" in readme
    assert "TestProject" in readme
