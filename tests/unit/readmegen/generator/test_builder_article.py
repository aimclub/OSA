import json

import pytest

from osa_tool.readmegen.generator.builder_article import MarkdownBuilderArticle


def example_overview():
    """
    Generate a JSON string containing an overview section.
    
    Returns:
        str: A JSON-formatted string with a single key ``overview`` mapping to a description of the overview section.
    """
    return json.dumps({"overview": "This is the overview section."})


def example_content():
    """
    Generate a JSON string containing a content section.
    
    Returns:
        str: A JSON-formatted string with a single key ``content`` mapping to the
        description of the content section.
    """
    return json.dumps({"content": "This is the content section."})


def example_algorithms():
    """
    Return a JSON string representing the algorithms section.
    
    This method serializes a dictionary containing a single key
    `algorithms` with a placeholder description into a JSON string.
    
    Returns:
        str: A JSON-formatted string with the algorithms information.
    """
    return json.dumps({"algorithms": "This is the algorithms section."})


@pytest.fixture
def markdown_builder(config_loader, mock_load_data_metadata):
    """
    Builds a MarkdownBuilderArticle instance using the provided configuration loader.
    
    This helper function constructs a `MarkdownBuilderArticle` by supplying
    example overview, content, and algorithm sections. It is intended for
    testing or demonstration purposes where a fully populated article object
    is required.
    
    Args:
        config_loader: The configuration loader to use for building the article.
        mock_load_data_metadata: Mock data metadata used for testing (currently unused).
    
    Returns:
        MarkdownBuilderArticle: An instance of `MarkdownBuilderArticle` initialized
        with the supplied `config_loader` and example overview, content, and
        algorithms.
    """
    return MarkdownBuilderArticle(
        config_loader=config_loader,
        overview=example_overview(),
        content=example_content(),
        algorithms=example_algorithms(),
    )


def test_load_template(markdown_builder):
    """
    Test that the markdown builder's load_template method returns a template containing required sections.
    
    Args:
        markdown_builder: The markdown builder instance to test.
    
    Returns:
        None
    """
    # Act
    template = markdown_builder.load_template()
    # Assert
    assert "headers" in template
    assert "overview" in template


def test_header_section(markdown_builder):
    """
    Test that the markdown builder's header contains the expected project name.
    
    Args:
        markdown_builder: The markdown builder instance whose header is being verified.
    
    Returns:
        None
    """
    # Act
    header = markdown_builder.header
    # Assert
    assert "TestProject" in header


def test_overview_section(markdown_builder):
    """
    Test that the MarkdownBuilder's overview section is correctly formatted.
    
    This test retrieves the `overview` property from the provided `markdown_builder` instance
    and verifies that it is a string, begins with the Markdown header "## Overview",
    and contains the expected overview text.
    
    Args:
        markdown_builder: An instance of a MarkdownBuilder (or similar) that exposes
            an `overview` property.
    
    Returns:
        None
    """
    # Act
    section = markdown_builder.overview
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Overview")
    assert "This is the overview section." in section


def test_content_section(markdown_builder):
    """
    Tests that the content section of a MarkdownBuilder instance is correctly
    formatted.
    
    This function retrieves the `content` property from the provided
    `markdown_builder` object and verifies that it is a string, starts with
    the expected heading "## Content", and contains the expected body text
    "This is the content section."
    
    Args:
        markdown_builder: An instance of a MarkdownBuilder (or similar) that
            exposes a `content` property representing the content section of
            a Markdown document.
    
    Returns:
        None
    
    Raises:
        AssertionError: If any of the conditions on the content string are
            not met.
    """
    # Act
    section = markdown_builder.content
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Content")
    assert "This is the content section." in section


def test_algorithms_section(markdown_builder):
    """
    Test that the algorithms section of a markdown builder is correctly formatted.
    
    This function retrieves the `algorithms` property from the provided
    `markdown_builder` instance and verifies that it is a string, starts with
    the expected heading, and contains the expected content.
    
    Parameters
    ----------
    markdown_builder
        The markdown builder instance whose algorithms section is to be tested.
    
    Returns
    -------
    None
        The function performs assertions and does not return a value.
    """
    # Act
    section = markdown_builder.algorithms
    # Assert
    assert isinstance(section, str)
    assert section.startswith("## Algorithms")
    assert "This is the algorithms section." in section


def test_build_readme(markdown_builder):
    """
    Test that the markdown_builder builds a README string containing expected sections.
    
    Parameters
    ----------
    markdown_builder
        The MarkdownBuilder instance used to generate the README.
    
    Returns
    -------
    None
        This test function does not return a value; it raises an AssertionError if the build fails.
    """
    # Act
    readme = markdown_builder.build()
    # Assert
    assert isinstance(readme, str)
    assert "## Overview" in readme
    assert "## Content" in readme
    assert "## Algorithms" in readme
    assert "TestProject" in readme
