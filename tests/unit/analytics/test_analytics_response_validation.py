from osa_tool.operations.analysis.repository_report.response_validation import (
    RepositoryReport,
    RepositoryStructure,
    ReadmeEvaluation,
    CodeDocumentation,
    OverallAssessment,
    YesNoPartial,
)


def test_repository_report_defaults():
    # Act
    report = RepositoryReport()

    # Assert
    assert report.structure.compliance == "Unknown"
    assert report.structure.missing_files == []
    assert report.readme.readme_quality == "Unknown"
    assert report.readme.project_description == YesNoPartial.UNKNOWN
    assert report.documentation.tests_present == YesNoPartial.UNKNOWN
    assert report.documentation.outdated_content is False
    assert report.assessment.key_shortcomings == ["There are no critical issues"]
    assert report.assessment.recommendations == ["No recommendations"]


def test_repository_report_with_custom_data():
    # Arrange
    custom_data = RepositoryReport(
        structure=RepositoryStructure(
            compliance="Partial",
            missing_files=["README.md", "LICENSE"],
            organization="Good",
        ),
        readme=ReadmeEvaluation(
            readme_quality="Good",
            project_description=YesNoPartial.YES,
            installation=YesNoPartial.PARTIAL,
            usage_examples=YesNoPartial.NO,
            contribution_guidelines=YesNoPartial.YES,
            license_specified=YesNoPartial.NO,
            badges_present=YesNoPartial.YES,
        ),
        documentation=CodeDocumentation(
            tests_present=YesNoPartial.YES,
            docs_quality="Detailed",
            outdated_content=True,
        ),
        assessment=OverallAssessment(
            key_shortcomings=["Missing LICENSE file", "Outdated API docs"],
            recommendations=["Add LICENSE", "Update documentation"],
        ),
    )

    # Assert
    assert custom_data.structure.missing_files == ["README.md", "LICENSE"]
    assert custom_data.readme.project_description == YesNoPartial.YES
    assert custom_data.documentation.outdated_content is True
    assert "Missing LICENSE file" in custom_data.assessment.key_shortcomings
    assert custom_data.assessment.recommendations == ["Add LICENSE", "Update documentation"]


def test_repository_report_enum_validation():
    # Act
    readme_eval = ReadmeEvaluation(project_description=YesNoPartial.YES)

    # Assert
    assert readme_eval.project_description == YesNoPartial.YES


def test_repository_report_ignores_extra_fields():
    # Act
    data_with_extra = {
        "structure": {
            "compliance": "Yes",
            "missing_files": [],
            "organization": "Excellent",
            "unexpected_field": "ignored",
        },
        "readme": {"readme_quality": "Good", "badges_present": "Partial", "extra_field": 123},
        "documentation": {"tests_present": "Yes", "docs_quality": "Good"},
        "assessment": {"key_shortcomings": [], "recommendations": []},
        "extra_top_level_field": "should be ignored",
    }
    report = RepositoryReport(**data_with_extra)

    # Assert
    assert not hasattr(report.structure, "unexpected_field")
    assert not hasattr(report.readme, "extra_field")
    assert not hasattr(report, "extra_top_level_field")


def test_repository_report_list_defaults_are_independent():
    # Arrange
    report1 = RepositoryReport()
    report2 = RepositoryReport()

    # Act
    report1.structure.missing_files.append("README.md")

    # Assert
    assert report1.structure.missing_files == ["README.md"]
    assert report2.structure.missing_files == []
