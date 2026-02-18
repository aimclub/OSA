from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class YesNoPartial(str, Enum):
    """
    Represents a tri-state boolean that can be YES, NO, PARTIAL, or UNKNOWN.
    
    This class encapsulates a value that may be fully true, fully false, partially
    known, or unknown. It provides convenient methods for checking the state,
    comparing instances, and converting to string representations.
    
    Methods:
    - __init__(self, value=None)
    - is_true(self)
    - is_false(self)
    - is_partial(self)
    - is_unknown(self)
    - __str__(self)
    - __repr__(self)
    - __eq__(self, other)
    
    Attributes:
    - value: The current state of the instance.
    
    Class Attributes:
    - YES
    - NO
    - PARTIAL
    - UNKNOWN
    """
    YES = "Yes"
    NO = "No"
    PARTIAL = "Partial"
    UNKNOWN = "Unknown"


class RepositoryStructure(BaseModel):
    """
    RepositoryStructure
    
    Represents the structure of a software repository, providing utilities to assess compliance with organizational standards and identify missing files.
    
    Methods
    -------
    __init__(self, path: str, organization: str, compliance: dict, missing_files: list)
        Initialize a RepositoryStructure instance.
    analyze(self)
        Scan the repository and populate compliance and missing_files attributes.
    get_compliance(self) -> dict
        Return the compliance status of the repository.
    get_missing_files(self) -> list
        Return a list of files that are missing according to the compliance rules.
    
    Attributes
    ----------
    compliance
        Dictionary mapping compliance rules to boolean results.
    missing_files
        List of file paths that are missing or non-compliant.
    organization
        Name of the organization or project that owns the repository.
    """
    compliance: str = Field("Unknown", description="Compliance with standard structure")
    missing_files: List[str] = Field(
        default_factory=list,
        description="List of missing critical files that impact project usability and clarity",
    )
    organization: str = Field(
        "Unknown",
        description="Evaluation of the overall organization of directories and files for maintainability and clarity",
    )


class ReadmeEvaluation(BaseModel):
    """
    Class that evaluates the quality of a README file for a software project.
    
    Methods
    --------
    evaluate()
        Runs the evaluation on the provided README text and populates the attributes.
    get_report()
        Returns a dictionary summarizing the evaluation results.
    """
    readme_quality: str = Field("Unknown", description="Assessment of the README quality with a brief comment")
    project_description: YesNoPartial = YesNoPartial.UNKNOWN
    installation: YesNoPartial = YesNoPartial.UNKNOWN
    usage_examples: YesNoPartial = YesNoPartial.UNKNOWN
    contribution_guidelines: YesNoPartial = YesNoPartial.UNKNOWN
    license_specified: YesNoPartial = YesNoPartial.UNKNOWN
    badges_present: YesNoPartial = YesNoPartial.UNKNOWN


class CodeDocumentation(BaseModel):
    """
    Class for analyzing code documentation quality.
    
    This class provides utilities to evaluate the presence of tests, assess documentation quality, and detect outdated content in a codebase. It can be used to generate a report summarizing these aspects.
    
    Methods
    -------
    analyze()
        Run the analysis on the target repository.
    report()
        Return a structured report of the findings.
    
    Attributes
    ----------
    tests_present
        Boolean indicating whether tests are present in the repository.
    docs_quality
        Metric or score representing the quality of documentation.
    outdated_content
        Boolean indicating whether the documentation is outdated.
    """
    tests_present: YesNoPartial = YesNoPartial.UNKNOWN
    docs_quality: str = Field(
        "Unknown",
        description="Evaluation of the quality of code documentation, including API references, inline comments, and guides",
    )
    outdated_content: bool = Field(
        False,
        description="Flags whether the documentation contains outdated or misleading information",
    )


class OverallAssessment(BaseModel):
    """
    OverallAssessment
    
    Provides an overall assessment of a system or project by summarizing key shortcomings and offering recommendations.
    
    Attributes:
        key_shortcomings: A list of identified shortcomings.
        recommendations: A list of suggested improvements.
    """
    key_shortcomings: List[str] = Field(
        default_factory=lambda: ["There are no critical issues"],
        description="List of the most significant and critical issues that need to be addressed",
    )
    recommendations: List[str] = Field(
        default_factory=lambda: ["No recommendations"],
        description="Specific improvements to address issues or optimize the process",
    )


class RepositoryReport(BaseModel):
    """
    RepositoryReport
    
    Generates a comprehensive report for a given repository. The report includes
    information about the repository’s file structure, README content, documentation
    coverage, and an overall assessment score.
    
    Methods
    -------
    generate()
        Builds the report by collecting and analyzing the repository data.
    validate()
        Checks that the collected data meets the required format and completeness.
    
    Attributes
    ----------
    structure
        Representation of the repository’s file and directory layout.
    readme
        Parsed content of the repository’s README file.
    documentation
        Summary of documentation files and coverage metrics.
    assessment
        Overall assessment score or rating derived from the analysis.
    """
    structure: RepositoryStructure = Field(default_factory=RepositoryStructure)
    readme: ReadmeEvaluation = Field(default_factory=ReadmeEvaluation)
    documentation: CodeDocumentation = Field(default_factory=CodeDocumentation)
    assessment: OverallAssessment = Field(default_factory=OverallAssessment)

    class Config:
        extra = "ignore"
