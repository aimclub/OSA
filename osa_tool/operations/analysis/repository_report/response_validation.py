from enum import Enum
from typing import Annotated

from pydantic import BaseModel


class YesNoPartial(str, Enum):
    YES = "Yes"
    NO = "No"
    PARTIAL = "Partial"
    UNKNOWN = "Unknown"


class RepositoryStructure(BaseModel):
    compliance: Annotated[str, "Compliance with standard structure"] = "Unknown"
    missing_files: Annotated[
        list[str],
        "List of missing critical files that impact project usability and clarity",
    ] = []
    organization: Annotated[
        str,
        "Evaluation of the overall organization of directories and files for maintainability and clarity",
    ] = "Unknown"


class ReadmeEvaluation(BaseModel):
    readme_quality: Annotated[str, "Assessment of the README quality with a brief comment"] = "Unknown"
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
        "Evaluation of the quality of code documentation, including API references, inline comments, and guides",
    ] = "Unknown"
    outdated_content: Annotated[
        bool,
        "Flags whether the documentation contains outdated or misleading information",
    ] = False


class OverallAssessment(BaseModel):
    key_shortcomings: Annotated[
        list[str],
        "List of the most significant and critical issues that need to be addressed",
    ] = ["There are no critical issues"]
    recommendations: Annotated[
        list[str],
        "Specific improvements to address issues or optimize the process",
    ] = ["No recommendations"]


class RepositoryReport(BaseModel):
    structure: RepositoryStructure = RepositoryStructure()
    readme: ReadmeEvaluation = ReadmeEvaluation()
    documentation: CodeDocumentation = CodeDocumentation()
    assessment: OverallAssessment = OverallAssessment()

    class Config:
        extra = "ignore"


class AfterReportBlock(BaseModel):
    name: str
    description: str
    tasks: list[tuple[str, bool]]


class AfterReport(BaseModel):
    summary: str
    blocks: list[AfterReportBlock]
