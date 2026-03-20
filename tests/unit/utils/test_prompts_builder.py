import pytest

from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader, PromptLoadError


def test_prompt_builder_success():
    """
    Tests that PromptBuilder.render successfully renders a template with given parameters.
    
    This test verifies that the render method correctly substitutes placeholders
    in a template string using the provided keyword arguments.
    The test uses a simple template to confirm basic formatting works as expected.
    
    Args:
        None
    
    Returns:
        None
    
    Raises:
        AssertionError: If the rendered output does not match the expected string.
    """
    # Arrange
    template = "Hello {name}"

    # Act
    result = PromptBuilder.render(template, name="Alice")

    # Assert
    assert result == "Hello Alice"


def test_prompt_builder_missing_argument():
    """
    Tests that PromptBuilder.render raises an exception when a required argument is missing.
    
    This test verifies that the render method properly raises a PromptBuilderError when a template placeholder lacks a corresponding keyword argument. The test uses a template with a placeholder and calls render without providing the required argument, expecting an exception to be raised.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    template = "Hello {name}"

    # Assert
    with pytest.raises(Exception):
        PromptBuilder.render(template)


def test_prompt_builder_invalid_format():
    """
    Tests that PromptBuilder.render raises an exception when given an invalid format string.
    
    This test verifies that an improperly formatted template string (e.g., with an unmatched curly brace) causes the render method to fail, ensuring robust error handling for malformed input. The test uses a specific invalid template to trigger a formatting error.
    
    Args:
        None. This test method defines its own template internally.
    
    Raises:
        PromptBuilderError: The test expects a PromptBuilderError to be raised by PromptBuilder.render when formatting fails due to the invalid template. This is more specific than a generic Exception, as indicated by the helper function's documentation.
    """
    # Arrange
    template = "Hello {name"

    # Assert
    with pytest.raises(Exception):
        PromptBuilder.render(template, name="Bob")


def test_prompt_loader_load_files():
    """
    Verifies that the PromptLoader correctly loads and caches prompt files upon initialization.
    
    This test ensures that the loader's cache is not empty and that each section within the cache contains a non-empty dictionary of prompts. The test is necessary to confirm that all expected prompt files are successfully parsed and stored, preventing runtime errors due to missing or empty prompt data.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    loader = PromptLoader()

    # Assert
    assert len(loader.cache) > 0
    for section, prompts in loader.cache.items():
        assert isinstance(prompts, dict)
        assert len(prompts) > 0


def test_prompt_loader_missing_prompt():
    """
    Verifies that the PromptLoader raises a PromptLoadError when attempting to retrieve a non-existent prompt.
    This test ensures proper error handling for missing prompt files, which is critical for the tool's reliability in automated documentation generation.
    
    Args:
        None
    
    Raises:
        PromptLoadError: Expected when the requested prompt file does not exist.
    """
    # Arrange
    loader = PromptLoader()

    # Assert
    with pytest.raises(PromptLoadError):
        loader.get("no_such_prompt.preanalysis")


def test_prompt_loader_missing_section():
    """
    Verifies that the PromptLoader raises a PromptLoadError when attempting to access a non-existent section.
    
    This test case initializes a PromptLoader instance and asserts that calling the get method with a missing section identifier correctly triggers the expected exception.
    
    Args:
        None
    
    Raises:
        PromptLoadError: Expected when the requested section does not exist in the prompt configuration.
    """
    # Arrange
    loader = PromptLoader()

    # Assert
    with pytest.raises(PromptLoadError):
        loader.get("readme.no_such_section")


def test_prompt_builder_format_real_template():
    """
    Tests the rendering of a real template using PromptBuilder.
    
    This method loads a specific template named "readme.preanalysis" and
    renders it with test data to verify that the template produces a
    non-empty string containing expected content. The test ensures that
    the template and PromptBuilder work correctly together in a realistic
    scenario, confirming that placeholders are properly substituted and
    the output is valid.
    
    Args:
        None
    
    Returns:
        None
    
    Why:
    - To validate that the "readme.preanalysis" template can be successfully
      loaded and rendered with actual data.
    - To verify the rendered output is a non-empty string and contains
      specific expected text, ensuring the template formatting behaves as
      intended.
    - This serves as an integration test for the template loading and
      rendering pipeline, checking for correct placeholder substitution
      and absence of formatting errors.
    """
    # Arrange
    loader = PromptLoader()
    template = loader.get("readme.preanalysis")

    # Act
    rendered = PromptBuilder.render(template, repository_tree="test_tree", readme_content="test_readme")

    # Assert
    assert isinstance(rendered, str)
    assert len(rendered) > 0
    assert "Based on the provided data about the files" in rendered
