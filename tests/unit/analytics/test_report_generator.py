from osa_tool.analytics.response_validation import (
    RepositoryReport,
    RepositoryStructure,
    ReadmeEvaluation,
    CodeDocumentation,
    OverallAssessment,
)
from osa_tool.utils.response_cleaner import JsonParseError


def test_make_request_success(text_generator_instance):
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
