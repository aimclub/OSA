import json

import pytest

from osa_tool.readmegen.generator.builder import MarkdownBuilder


def example_overview():
    return json.dumps({"overview": "This project does amazing things with AI."})


def example_core_features():
    return json.dumps(
        [
            {
                "feature_name": "Fast Inference",
                "feature_description": "Performs prediction in under 10ms",
                "is_critical": True,
            },
            {
                "feature_name": "Modular Design",
                "feature_description": "Easily plug in new components",
                "is_critical": False,
            },
            {
                "feature_name": "API Ready",
                "feature_description": "Exposes a REST API for integration",
                "is_critical": True,
            },
        ]
    )


def example_getting_started():
    return json.dumps(
        {"getting_started": "To get started, install the package and run `main.py`."}
    )


@pytest.fixture
def markdown_builder(config_loader):
    return MarkdownBuilder(
        config_loader=config_loader,
        overview=example_overview(),
        core_features=example_core_features(),
        getting_started=example_getting_started(),
    )


def test_template_loading(markdown_builder):
    # Act
    template = markdown_builder.load_template()
    # Assert
    assert isinstance(template, dict)
    assert "overview" in template
    assert "core_features" in template
    assert "getting_started" in template


def test_overview_section(markdown_builder):
    # Act
    section = markdown_builder.overview
    # Assert
    assert "This project does amazing things" in section
    assert section.startswith("## Overview")
    assert "This project" in section


def test_core_features_section(markdown_builder):
    # Act
    section = markdown_builder.core_features
    # Assert
    assert "Fast Inference" in section
    assert "API Ready" in section
    assert "Modular Design" not in section
    assert section.startswith("## Core features")


def test_getting_started_section(markdown_builder):
    # Act
    section = markdown_builder.getting_started
    # Assert
    assert "install the package" in section
    assert section.startswith("## Getting Started")


def test_installation_section(markdown_builder):
    # Act
    section = markdown_builder.installation
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Installation")


def test_header_section(markdown_builder):
    # Act
    section = markdown_builder.header
    # Assert
    assert isinstance(section, str)
    assert section.startswith("# ")


def test_examples_section_optional(markdown_builder):
    # Act
    section = markdown_builder.examples
    # Assert
    assert isinstance(section, str)


def test_documentation_section(markdown_builder):
    # Act
    section = markdown_builder.documentation
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Documentation") or section == ""


def test_contributing_section(markdown_builder):
    # Act
    section = markdown_builder.contributing
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Contributing") or section == ""


def test_license_section(markdown_builder):
    # Act
    section = markdown_builder.license
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## License") or section == ""


def test_citation_section(markdown_builder):
    # Act
    section = markdown_builder.citation
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Citation")


def test_table_of_contents(markdown_builder):
    # Act
    toc = markdown_builder.table_of_contents
    # Assert
    assert "Table of Contents" in toc
    assert "- [Core features](#core-features)" in toc


def test_full_readme_build(markdown_builder):
    # Act
    readme = markdown_builder.build()
    # Assert
    assert isinstance(readme, str)
    assert "# " in readme
    assert "## Overview" in readme
    assert "## Core features" in readme
    assert "## Installation" in readme
    assert "## Getting Started" in readme
    assert "## Table of Contents" in readme
