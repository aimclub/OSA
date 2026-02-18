from unittest.mock import MagicMock, patch


def test_text_generator_initialization(text_generator):
    """
    Test that the TextGenerator is initialized correctly.
    
    This test verifies that the `text_generator` instance has been set up with the
    expected configuration and that its `model_handler` attribute is a mock object
    used for testing.
    
    Parameters
    ----------
    text_generator
        The TextGenerator instance to test.
    
    Returns
    -------
    None
        The function does not return a value; it raises an AssertionError if the
        initialization does not match the expected values.
    """
    # Assert
    assert text_generator.config.git.repository == "https://github.com/testuser/testrepo.git"
    assert isinstance(text_generator.model_handler, MagicMock)


@patch("json.loads", return_value={})
@patch(
    "osa_tool.analytics.prompt_builder.RepositoryReport.model_validate",
    return_value=MagicMock(),
)
def test_make_request(mock_parse_obj, mock_json_loads, text_generator):
    """
    Test that `TextGenerator.make_request` returns a mocked report object.
    
    This test verifies that the `make_request` method of the `text_generator`
    instance returns a `MagicMock` instance when the external dependencies
    (`json.loads` and `RepositoryReport.model_validate`) are patched to
    return empty structures.
    
    Args:
        mock_parse_obj: Mock object for the `parse_obj` method used within
            the test environment.
        mock_json_loads: Mock object for the `json.loads` function.
        text_generator: The `TextGenerator` instance whose `make_request`
            method is being tested.
    
    Returns:
        None
    """
    # Act
    report = text_generator.make_request()
    # Assert
    assert isinstance(report, MagicMock)


@patch("builtins.open", new_callable=MagicMock)
@patch(
    "osa_tool.analytics.report_generator.tomllib.load",
    return_value={"prompt": {"main_prompt": "Prompt"}},
)
def test_build_prompt(mock_tomllib_load, mock_open, text_generator):
    """
    Test that the `_build_prompt` method returns the expected prompt string.
    
    Parameters
    ----------
    mock_tomllib_load : MagicMock
        Mocked `tomllib.load` function returning a dictionary with a `main_prompt`.
    mock_open : MagicMock
        Mocked `builtins.open` used by the text generator.
    text_generator : TextGenerator
        Instance of the class under test.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the prompt is correctly built.
    """
    # Act
    prompt = text_generator._build_prompt()
    # Assert
    assert prompt == "Prompt"


def test_extract_presence_files(text_generator):
    """
    Test the extraction of presence information for various repository files.
    
    This test configures the `text_generator.sourcerank` mock methods to simulate the presence
    of specific files and then verifies that the private method `_extract_presence_files`
    returns the expected formatted list of presence statements.
    
    Parameters
    ----------
    text_generator
        The test fixture providing a `text_generator` instance whose `sourcerank`
        attribute contains methods for checking the presence of README, LICENSE,
        examples, documentation, and requirements files.
    
    Returns
    -------
    None
        This function does not return a value; it asserts that the result of
        `_extract_presence_files` matches the expected list.
    """
    # Arrange
    text_generator.sourcerank.readme_presence = MagicMock(return_value=True)
    text_generator.sourcerank.license_presence = MagicMock(return_value=False)
    text_generator.sourcerank.examples_presence = MagicMock(return_value="Partial")
    text_generator.sourcerank.docs_presence = MagicMock(return_value=True)
    text_generator.sourcerank.requirements_presence = MagicMock(return_value=True)
    expected = [
        "README presence is True",
        "LICENSE presence is False",
        "Examples presence is Partial",
        "Documentation presence is True",
        "Requirements presence is True",
    ]
    # Act
    result = text_generator._extract_presence_files()
    # Assert
    assert result == expected
