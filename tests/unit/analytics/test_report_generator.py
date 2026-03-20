from osa_tool.operations.analysis.repository_report.response_validation import (
    RepositoryReport,
    RepositoryStructure,
    ReadmeEvaluation,
    CodeDocumentation,
    OverallAssessment,
)
from osa_tool.utils.response_cleaner import JsonParseError


def test_make_request_success(text_generator_instance):
    """
    Verifies that the make_request method successfully returns a valid RepositoryReport when the model handler provides a correct response.
    
    This test ensures the AfterReportTextGenerator correctly processes a valid model response into a properly structured RepositoryReport object, validating key fields across the report's structure, readme, documentation, and assessment sections.
    
    Args:
        text_generator_instance: A fixture providing a tuple containing the AfterReportTextGenerator instance and its mocked model handler. The mock is configured to return a predefined valid RepositoryReport.
    
    Returns:
        None.
    """
    # Arrange
    text_generator, mock_model_handler = text_generator_instance
    valid_response = {
        "structure": {"compliance": "Yes", "missing_files": [], "organization": "Well-organized"},
        "readme": {
            "readme_quality": "High quality with clear instructions",
            "project_description": "Yes",
            "installation": "Yes",
            "usage_examples": "Partial",
            "contribution_guidelines": "No",
            "license_specified": "Yes",
            "badges_present": "Partial",
        },
        "documentation": {
            "tests_present": "Yes",
            "docs_quality": "Comprehensive and up-to-date",
            "outdated_content": False,
        },
        "assessment": {
            "key_shortcomings": ["Missing contribution guidelines"],
            "recommendations": ["Add a CONTRIBUTING.md file with guidelines"],
        },
    }
    mock_model_handler.send_and_parse.return_value = RepositoryReport.model_validate(valid_response)

    # Act
    report = text_generator.make_request()

    # Assert
    assert isinstance(report, RepositoryReport)
    assert report.structure.compliance == "Yes"
    assert report.readme.project_description == "Yes"
    assert report.documentation.tests_present == "Yes"
    assert "Missing contribution guidelines" in report.assessment.key_shortcomings


def test_make_request_invalid_json(text_generator_instance):
    """
    Verifies that the make_request method returns a default RepositoryReport when the model handler encounters a JSON parsing error.
    This ensures the text generator gracefully handles parsing failures by providing a safe, empty report rather than propagating the error.
    
    Args:
        text_generator_instance: A fixture providing a tuple containing the text generator instance and its associated mock model handler.
    
    Returns:
        None.
    """
    # Arrange
    text_generator, mock_model_handler = text_generator_instance
    mock_model_handler.send_and_parse.side_effect = JsonParseError("Invalid JSON")

    # Act
    report = text_generator.make_request()

    # Assert
    assert isinstance(report, RepositoryReport)
    assert report.structure == RepositoryStructure()
    assert report.readme == ReadmeEvaluation()
    assert report.documentation == CodeDocumentation()
    assert report.assessment == OverallAssessment()
