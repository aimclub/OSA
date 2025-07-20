from unittest.mock import MagicMock, patch


def test_text_generator_initialization(text_generator):
    # Assert
    assert text_generator.config.git.repository == "https://github.com/testuser/testrepo.git"
    assert isinstance(text_generator.model_handler, MagicMock)


@patch("json.loads", return_value={})
@patch(
    "osa_tool.analytics.prompt_builder.RepositoryReport.model_validate",
    return_value=MagicMock(),
)
def test_make_request(mock_parse_obj, mock_json_loads, text_generator):
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
    # Act
    prompt = text_generator._build_prompt()
    # Assert
    assert prompt == "Prompt"


def test_extract_presence_files(text_generator):
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
