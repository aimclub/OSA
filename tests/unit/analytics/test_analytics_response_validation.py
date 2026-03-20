from osa_tool.operations.analysis.repository_report.response_validation import (
    RepositoryReport,
    RepositoryStructure,
    ReadmeEvaluation,
    CodeDocumentation,
    OverallAssessment,
    YesNoPartial,
)


def test_repository_report_defaults():
    """
    Verifies that a new instance of RepositoryReport is initialized with the correct default values.
    
    This test case checks the default state of various nested components within the
    RepositoryReport class, including structure, readme, documentation, and assessment
    attributes, ensuring they align with expected initial constants and enums.
    This is important to confirm that the report starts in a consistent, predictable state
    before any analysis or data is added.
    
    Args:
        None
    
    Returns:
        None
    """
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
    """
    Verifies that the RepositoryReport and its nested components correctly store and retrieve custom data.
    
    This test case manually instantiates a RepositoryReport object with specific values for its structure, readme, documentation, and assessment attributes, then asserts that the assigned values are correctly preserved. The test ensures that the data model's nested structure functions as intended, allowing custom data to be set and retrieved without loss or corruption.
    
    Args:
        None: This is a test function and does not accept parameters.
    
    Returns:
        None: This is a test function and does not return a value.
    """
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
    """
    Verifies that the repository report correctly validates and stores enum values for its fields.
    This test ensures that the ReadmeEvaluation class properly accepts and retains a valid enum value (YesNoPartial.YES) for the project_description field.
    
    Args:
        None.
    
    Returns:
        None.
    """
    # Act
    readme_eval = ReadmeEvaluation(project_description=YesNoPartial.YES)

    # Assert
    assert readme_eval.project_description == YesNoPartial.YES


def test_repository_report_ignores_extra_fields():
    """
    Verifies that the RepositoryReport class and its nested structures ignore any extra or unexpected fields provided during initialization.
    
    This test ensures that when a dictionary containing additional keys is unpacked into the RepositoryReport constructor, the resulting object and its sub-components (structure and readme) only retain the expected attributes and do not dynamically assign the extra fields. This is important to maintain a strict, predictable schema for the report data and prevent accidental pollution of the object with arbitrary fields.
    
    Args:
        None
    """
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
    """
    Verifies that default values in RepositoryReport instances are independent and not shared.
    
    This test ensures that modifying a collection (like missing_files) in one instance of RepositoryReport does not affect other instances, confirming that default values are correctly initialized as unique objects rather than class-level shared state. This is important because mutable default values (like lists) defined at the class level would be shared across all instances, leading to unintended side effects.
    
    Args:
        None.
    
    Returns:
        None.
    """
    # Arrange
    report1 = RepositoryReport()
    report2 = RepositoryReport()

    # Act
    report1.structure.missing_files.append("README.md")

    # Assert
    assert report1.structure.missing_files == ["README.md"]
    assert report2.structure.missing_files == []
