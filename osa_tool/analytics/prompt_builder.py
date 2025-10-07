from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


class YesNoPartial(str, Enum):
    YES = "Yes"
    NO = "No"
    PARTIAL = "Partial"
    UNKNOWN = "Unknown"


class RepositoryStructure(BaseModel):
    compliance: Annotated[str, Field(description="Compliance with standard structure")] = "Unknown"
    missing_files: Annotated[
        list[str],
        Field(description="List of missing critical files that impact project usability and clarity"),
    ] = []
    organization: Annotated[
        str,
        Field(
            description="Evaluation of the overall organization of directories and files for maintainability and clarity"
        ),
    ] = "Unknown"


class ReadmeEvaluation(BaseModel):
    readme_quality: Annotated[str, Field(description="Assessment of the README quality with a brief comment")] = (
        "Unknown"
    )
    project_description: YesNoPartial = YesNoPartial.UNKNOWN
    installation: YesNoPartial = YesNoPartial.UNKNOWN
    usage_examples: YesNoPartial = YesNoPartial.UNKNOWN
    contribution_guidelines: YesNoPartial = YesNoPartial.UNKNOWN
    license_specified: YesNoPartial = YesNoPartial.UNKNOWN
    badges_present: YesNoPartial = YesNoPartial.UNKNOWN


class CodeDocumentation(BaseModel):
    tests_present: YesNoPartial = YesNoPartial.UNKNOWN
    docs_quality: Annotated[
        str,
        Field(
            description="Evaluation of the quality of code documentation, including API references, inline comments, and guides"
        ),
    ] = "Unknown"
    outdated_content: Annotated[
        bool,
        Field(description="Flags whether the documentation contains outdated or misleading information"),
    ] = False


class OverallAssessment(BaseModel):
    key_shortcomings: Annotated[
        list[str],
        Field(description="List of the most significant and critical issues that need to be addressed"),
    ] = ["There are no critical issues"]
    recommendations: Annotated[
        list[str],
        Field(description="Specific improvements to address issues or optimize the process"),
    ] = ["No recommendations"]


class RepositoryReport(BaseModel):
    structure: RepositoryStructure = RepositoryStructure()
    readme: ReadmeEvaluation = ReadmeEvaluation()
    documentation: CodeDocumentation = CodeDocumentation()
    assessment: OverallAssessment = OverallAssessment()

    class Config:
        extra = "ignore"
