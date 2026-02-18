import json

import pytest

from osa_tool.readmegen.generator.builder import MarkdownBuilder


def example_overview():
    """
    Returns a JSON-formatted string containing a brief project overview.
    
    Returns:
        str: A JSON string with a single key 'overview' describing the project.
    """
    return json.dumps({"overview": "This project does amazing things with AI."})


def example_core_features():
    """
    Returns a JSON string containing a list of core feature descriptions.
    
    The JSON string represents an array of objects, each describing a feature with its name, description, and whether it is critical.
    
    Returns:
        str: A JSON-formatted string of feature information.
    """
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
    """
    Gets a JSON string with a getting started message.
    
    Returns:
        str: A JSON-formatted string containing a ``"getting_started"`` key with
        instructions on how to install the package and run ``main.py``.
    """
    return json.dumps({"getting_started": "To get started, install the package and run `main.py`."})


@pytest.fixture
def markdown_builder(config_loader, mock_load_data_metadata):
    """
    Builds and returns a MarkdownBuilder instance configured with example data.
    
        Parameters
        ----------
        config_loader
            The configuration loader used to initialize the MarkdownBuilder.
        mock_load_data_metadata
            A mock data loader for metadata (currently unused in this function).
    
        Returns
        -------
        MarkdownBuilder
            A new MarkdownBuilder object initialized with the provided configuration
            loader and example overview, core features, and getting started sections.
    """
    return MarkdownBuilder(
        config_loader=config_loader,
        overview=example_overview(),
        core_features=example_core_features(),
        getting_started=example_getting_started(),
    )


def test_template_loading(markdown_builder):
    """
    Test that the markdown builder loads a template correctly.
    
    Parameters
    ----------
    markdown_builder
        The MarkdownBuilder instance used to load the template.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the template is a dictionary containing the expected keys.
    """
    # Act
    template = markdown_builder.load_template()
    # Assert
    assert isinstance(template, dict)
    assert "overview" in template
    assert "core_features" in template
    assert "getting_started" in template


def test_overview_section(markdown_builder):
    """
    Test that the overview section of the markdown builder contains expected content.
    
    Parameters
    ----------
    markdown_builder
        The markdown builder instance whose `overview` property is being tested.
    
    Returns
    -------
    None
        This function does not return a value; it raises an AssertionError if the
        overview section does not contain the expected text.
    """
    # Act
    section = markdown_builder.overview
    # Assert
    assert "This project does amazing things" in section
    assert section.startswith("## Overview")
    assert "This project" in section


def test_core_features_section(markdown_builder):
    """
    Test that the core features section of the markdown builder contains expected headings and content.
    
    Args:
        markdown_builder: The markdown builder instance whose core_features property is being tested.
    
    Returns:
        None
    
    This test verifies that the 'core_features' section includes the strings "Fast Inference" and "API Ready", does not include "Modular Design", and starts with the heading "## Core features".
    """
    # Act
    section = markdown_builder.core_features
    # Assert
    assert "Fast Inference" in section
    assert "API Ready" in section
    assert "Modular Design" not in section
    assert section.startswith("## Core features")


def test_getting_started_section(markdown_builder):
    """
    Test that the `getting_started` section of the markdown builder contains the expected
    content.
    
    Parameters
    ----------
    markdown_builder
        The markdown builder instance whose `getting_started` property is to be tested.
    
    Returns
    -------
    None
        This function does not return a value; it performs assertions on the section string.
    """
    # Act
    section = markdown_builder.getting_started
    # Assert
    assert "install the package" in section
    assert section.startswith("## Getting Started")


def test_installation_section(markdown_builder):
    """
    Test that the installation section of the markdown builder is a string starting with '## Installation'.
    
    Parameters
    ----------
    markdown_builder
        The markdown builder instance whose installation property is to be tested.
    
    Returns
    -------
    None
        This function performs assertions and does not return a value.
    """
    # Act
    section = markdown_builder.installation
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Installation")


def test_header_section(markdown_builder):
    """
    Test that the header section of the markdown builder is correctly formatted.
    
    Args:
        markdown_builder: The markdown builder instance whose header property is to be tested.
    
    Returns:
        None
    
    This test verifies that the `header` attribute of the provided `markdown_builder` is a string
    that begins with a single hash character followed by a space, indicating a level‑1 Markdown
    heading. It uses assertions to enforce these conditions.
    """
    # Act
    section = markdown_builder.header
    # Assert
    assert isinstance(section, str)
    assert section.startswith("# ")


def test_examples_section_optional(markdown_builder):
    """
    Test that the examples section of the markdown builder is optional and returns a string.
    
    Args:
        markdown_builder: The markdown builder instance to test.
    
    Returns:
        None
    """
    # Act
    section = markdown_builder.examples
    # Assert
    assert isinstance(section, str)


def test_documentation_section(markdown_builder):
    """
    Test that the documentation section of a MarkdownBuilder is a string and starts with
    '## Documentation' or is empty.
    
    Args:
        markdown_builder: The MarkdownBuilder instance whose documentation property is
            being verified.
    
    Returns:
        None
    
    Raises:
        AssertionError: If the documentation section is not a string or does not start
            with the expected prefix.
    """
    # Act
    section = markdown_builder.documentation
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Documentation") or section == ""


def test_contributing_section(markdown_builder):
    """
    Test that the markdown builder's contributing section is correctly formatted.
    
    This test retrieves the `contributing` property from the provided `markdown_builder`
    instance and verifies that it is a string. It also checks that the string either
    starts with the header "## Contributing" or is an empty string, ensuring that
    the contributing section is either properly generated or omitted.
    
    Parameters
    ----------
    markdown_builder
        The markdown builder instance whose `contributing` property is being tested.
    
    Returns
    -------
    None
        This function does not return a value; it raises an AssertionError if the
        test conditions are not met.
    """
    # Act
    section = markdown_builder.contributing
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Contributing") or section == ""


def test_license_section(markdown_builder):
    """
    Test that the license section of the markdown builder is a string and properly formatted.
    
    Args:
        markdown_builder: The markdown builder instance whose license property is being tested.
    
    Returns:
        None
    
    Raises:
        AssertionError: If the license section is not a string or does not start with "## License" unless it is empty.
    """
    # Act
    section = markdown_builder.license
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## License") or section == ""


def test_citation_section(markdown_builder):
    """
    Test that the MarkdownBuilder's citation section is correctly formatted.
    
    This test retrieves the `citation` property from the provided `markdown_builder` instance
    and verifies that it is a string beginning with the expected heading.
    
    Parameters
    ----------
    markdown_builder
        An instance of a MarkdownBuilder (or similar) that exposes a `citation` property.
    
    Returns
    -------
    None
        This function does not return a value; it raises an AssertionError if the
        expectations are not met.
    """
    # Act
    section = markdown_builder.citation
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Citation")


def test_table_of_contents(markdown_builder):
    """
    Test that the MarkdownBuilder generates a table of contents containing the expected entries.
    
    This test retrieves the `toc` property from the provided `markdown_builder` instance and
    verifies that it includes the heading "Table of Contents" as well as a link to the
    "Core features" section.
    
    Args:
        markdown_builder: An object that provides a `toc` attribute containing the
            generated table of contents string.
    
    Returns:
        None
    
    Raises:
        AssertionError: If the expected strings are not present in the table of contents.
    """
    # Act
    toc = markdown_builder.toc
    # Assert
    assert "Table of Contents" in toc
    assert "- [Core features](#core-features)" in toc


def test_full_readme_build(markdown_builder):
    """
    Test that the markdown_builder builds a complete README string.
    
    Args:
        markdown_builder: The MarkdownBuilder instance used to generate the README.
    
    Returns:
        None
    
    The test verifies that the returned README is a string and contains the
    expected top-level headings such as "# ", "## Overview", "## Core features",
    "## Installation", "## Getting Started", and "## Table of Contents".
    """
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
