from pydantic import BaseModel, Field
from typing import List
from enum import Enum


class YesNoPartial(str, Enum):
    YES = "Yes"
    NO = "No"
    PARTIAL = "Partial"
    UNKNOWN = "Unknown"


class RepositoryStructure(BaseModel):
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
    readme_quality: str = Field("Unknown", description="Assessment of the README quality with a brief comment")
    project_description: YesNoPartial = YesNoPartial.UNKNOWN
    installation: YesNoPartial = YesNoPartial.UNKNOWN
    usage_examples: YesNoPartial = YesNoPartial.UNKNOWN
    contribution_guidelines: YesNoPartial = YesNoPartial.UNKNOWN
    license_specified: YesNoPartial = YesNoPartial.UNKNOWN
    badges_present: YesNoPartial = YesNoPartial.UNKNOWN


class CodeDocumentation(BaseModel):
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
    key_shortcomings: List[str] = Field(
        default_factory=lambda: ["There are no critical issues"],
        description="List of the most significant and critical issues that need to be addressed",
    )
    recommendations: List[str] = Field(
        default_factory=lambda: ["No recommendations"],
        description="Specific improvements to address issues or optimize the process",
    )


class RepositoryReport(BaseModel):
    structure: RepositoryStructure = Field(default_factory=RepositoryStructure)
    readme: ReadmeEvaluation = Field(default_factory=ReadmeEvaluation)
    documentation: CodeDocumentation = Field(default_factory=CodeDocumentation)
    assessment: OverallAssessment = Field(default_factory=OverallAssessment)

    class Config:
        extra = "ignore"
