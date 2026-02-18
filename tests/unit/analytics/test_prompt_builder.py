from osa_tool.analytics.prompt_builder import RepositoryReport, YesNoPartial


# Tests for RepositoryReport with default values.
def test_structure_defaults(default_report):
    """
    Test that the default structure attributes of a report are correctly initialized.
    
    Parameters
    ----------
    default_report
        The report instance whose structure defaults are to be verified.
    
    Returns
    -------
    None
    
    This test asserts that the `compliance`, `missing_files`, and `organization` fields of
    `default_report.structure` are set to their expected default values:
    `"Unknown"`, an empty list, and `"Unknown"` respectively.
    """
    assert default_report.structure.compliance == "Unknown"
    assert default_report.structure.missing_files == []
    assert default_report.structure.organization == "Unknown"


def test_readme_defaults(default_report):
    """
    Test that the default values for the README fields are set correctly.
    
    This test verifies that a freshly created report has the expected default
    values for all README-related metrics. It checks that the quality of the
    README is marked as ``"Unknown"`` and that each of the other boolean-like
    attributes is set to ``YesNoPartial.UNKNOWN``.
    
    Args:
        default_report: A report instance that contains a ``readme`` attribute
            with the following properties:
            - readme_quality
            - project_description
            - installation
            - usage_examples
            - contribution_guidelines
            - license_specified
            - badges_present
    
    Returns:
        None
    
    Raises:
        AssertionError: If any of the README attributes do not match the
        expected default values.
    """
    assert default_report.readme.readme_quality == "Unknown"
    assert default_report.readme.project_description == YesNoPartial.UNKNOWN
    assert default_report.readme.installation == YesNoPartial.UNKNOWN
    assert default_report.readme.usage_examples == YesNoPartial.UNKNOWN
    assert default_report.readme.contribution_guidelines == YesNoPartial.UNKNOWN
    assert default_report.readme.license_specified == YesNoPartial.UNKNOWN
    assert default_report.readme.badges_present == YesNoPartial.UNKNOWN


def test_documentation_defaults(default_report):
    """
    Test that the default documentation values are correctly initialized.
    
    This test verifies that a `default_report` object's documentation attributes
    have the expected default values:
    * `tests_present` should be `YesNoPartial.UNKNOWN`.
    * `docs_quality` should be the string `"Unknown"`.
    * `outdated_content` should be `False`.
    
    Parameters
    ----------
    default_report
        The report instance whose documentation defaults are being checked.
    
    Returns
    -------
    None
        The function performs assertions and does not return a value.
    """
    assert default_report.documentation.tests_present == YesNoPartial.UNKNOWN
    assert default_report.documentation.docs_quality == "Unknown"
    assert default_report.documentation.outdated_content is False


def test_assessment_defaults(default_report):
    """
    Test that the default assessment has the expected default key shortcomings and recommendations.
    
    Args:
        default_report: The report object whose assessment defaults are to be verified.
    
    Returns:
        None
    
    Raises:
        AssertionError: If the assessment defaults do not match the expected values.
    """
    assert default_report.assessment.key_shortcomings == ["There are no critical issues"]
    assert default_report.assessment.recommendations == ["No recommendations"]


# Tests for RepositoryReport with custom-defined values.
def test_structure_custom(custom_report):
    """
    Test that a custom report has the expected structure attributes.
    
    Parameters
    ----------
    custom_report
        The report object to be tested. It is expected to expose a `structure` attribute
        containing the properties `compliance`, `missing_files`, and `organization`.
    
    Returns
    -------
    None
        The function performs assertions and does not return a value.
    """
    assert custom_report.structure.compliance == "Good"
    assert custom_report.structure.missing_files == ["setup.py"]
    assert custom_report.structure.organization == "Well structured"


def test_readme_custom(custom_report):
    """
    Test that a custom report's README metadata meets expected values.
    
    This test verifies that the `readme_quality` attribute of the report's README
    is set to `"Good"` and that the `project_description` attribute is marked as
    `YesNoPartial.YES`. It uses simple assertions to confirm these conditions.
    
    Args:
        custom_report: The report instance whose README properties are to be
            validated. The object is expected to expose a `readme` attribute with
            `readme_quality` and `project_description` fields.
    
    Returns:
        None
    """
    assert custom_report.readme.readme_quality == "Good"
    assert custom_report.readme.project_description == YesNoPartial.YES


def test_documentation_custom(custom_report):
    """
    Test that a custom report's documentation attributes meet expected values.
    
    Parameters
    ----------
    custom_report
        The report object containing a documentation attribute with properties
        `tests_present`, `docs_quality`, and `outdated_content`.
    
    Returns
    -------
    None
        This method performs assertions and does not return a value.
    """
    assert custom_report.documentation.tests_present == YesNoPartial.YES
    assert custom_report.documentation.docs_quality == "High"
    assert custom_report.documentation.outdated_content is True


def test_assessment_custom(custom_report):
    """
    Test that a custom report contains the expected assessment shortcomings and recommendations.
    
    Parameters
    ----------
    custom_report
        The report object to be tested. It is expected to expose an `assessment` attribute
        with `key_shortcomings` and `recommendations` properties.
    
    Returns
    -------
    None
    
    Raises
    ------
    AssertionError
        If the assessment's `key_shortcomings` or `recommendations` do not match the
        expected values.
    """
    assert custom_report.assessment.key_shortcomings == ["No CI/CD"]
    assert custom_report.assessment.recommendations == ["Add GitHub Actions"]


def test_extra_fields_ignored():
    """
    Test that RepositoryReport ignores unexpected keyword arguments.
    
    This test verifies that when a RepositoryReport is instantiated with an
    extra keyword argument that is not defined as a field, the resulting
    object does not expose that attribute.
    
    Returns:
        None
    """
    report = RepositoryReport(extra_field="This should be ignored")
    assert not hasattr(report, "extra_field")
