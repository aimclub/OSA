from osa_tool.analytics.prompt_builder import RepositoryReport, YesNoPartial


# Tests for RepositoryReport with default values.
def test_structure_defaults(default_report):
    assert default_report.structure.compliance == "Unknown"
    assert default_report.structure.missing_files == []
    assert default_report.structure.organization == "Unknown"


def test_readme_defaults(default_report):
    assert default_report.readme.readme_quality == "Unknown"
    assert default_report.readme.project_description == YesNoPartial.UNKNOWN
    assert default_report.readme.installation == YesNoPartial.UNKNOWN
    assert default_report.readme.usage_examples == YesNoPartial.UNKNOWN
    assert default_report.readme.contribution_guidelines == YesNoPartial.UNKNOWN
    assert default_report.readme.license_specified == YesNoPartial.UNKNOWN
    assert default_report.readme.badges_present == YesNoPartial.UNKNOWN


def test_documentation_defaults(default_report):
    assert default_report.documentation.tests_present == YesNoPartial.UNKNOWN
    assert default_report.documentation.docs_quality == "Unknown"
    assert default_report.documentation.outdated_content is False


def test_assessment_defaults(default_report):
    assert default_report.assessment.key_shortcomings == ["There are no critical issues"]
    assert default_report.assessment.recommendations == ["No recommendations"]


# Tests for RepositoryReport with custom-defined values.
def test_structure_custom(custom_report):
    assert custom_report.structure.compliance == "Good"
    assert custom_report.structure.missing_files == ["setup.py"]
    assert custom_report.structure.organization == "Well structured"


def test_readme_custom(custom_report):
    assert custom_report.readme.readme_quality == "Good"
    assert custom_report.readme.project_description == YesNoPartial.YES


def test_documentation_custom(custom_report):
    assert custom_report.documentation.tests_present == YesNoPartial.YES
    assert custom_report.documentation.docs_quality == "High"
    assert custom_report.documentation.outdated_content is True


def test_assessment_custom(custom_report):
    assert custom_report.assessment.key_shortcomings == ["No CI/CD"]
    assert custom_report.assessment.recommendations == ["Add GitHub Actions"]


def test_extra_fields_ignored():
    report = RepositoryReport(extra_field="This should be ignored")
    assert not hasattr(report, "extra_field")