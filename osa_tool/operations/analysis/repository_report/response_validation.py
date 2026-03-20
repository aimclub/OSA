from enum import Enum
from typing import Annotated

from pydantic import BaseModel
from pydantic import RootModel


class YesNoPartial(str, Enum):
    """
    Represents a ternary logic state for yes/no/partial/unknown conditions.
    
        Class Attributes:
        - YES
        - NO
        - PARTIAL
        - UNKNOWN
    
        Attributes:
        - value: The current state value.
    
        Methods:
        - __init__: Initializes with a value.
        - __eq__: Compares with another YesNoPartial instance.
        - __str__: Returns string representation.
        - __repr__: Returns formal string representation.
        - from_string: Creates instance from string.
        - to_string: Converts instance to string.
        - is_yes: Checks if value is YES.
        - is_no: Checks if value is NO.
        - is_partial: Checks if value is PARTIAL.
        - is_unknown: Checks if value is UNKNOWN.
    """

    YES = "Yes"
    NO = "No"
    PARTIAL = "Partial"
    UNKNOWN = "Unknown"


class RepositoryStructure(BaseModel):
    """
    RepositoryStructure class for analyzing and validating the structure of open-source repositories.
    
        This class provides functionality to analyze repository structures against predefined
        templates, validate compliance with organizational standards, and identify missing
        required files or directories. It serves as a core component for repository quality
        assessment and standardization workflows.
    
        Attributes:
            compliance (bool): Indicates whether the repository structure complies with
                the required template and organizational standards.
            missing_files (list): A list of file paths that are required but missing
                from the repository structure.
            organization (str): The organizational template or standard against which
                the repository structure is being validated.
    
        Methods:
            __init__: Initializes the RepositoryStructure with a given repository path
                and optional organizational template.
            analyze: Performs a comprehensive analysis of the repository structure,
                comparing it against the specified organizational template.
            validate: Validates the repository structure for compliance, updating the
                compliance attribute and populating the list of missing files.
            get_summary: Generates a summary report of the repository structure analysis,
                including compliance status and missing files.
    """

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
    """
    ReadmeEvaluation class evaluates the quality of a README file based on various criteria.
    
        Attributes:
            readme_quality: Overall quality score of the README.
            project_description: Score for the project description section.
            installation: Score for the installation instructions.
            usage_examples: Score for the usage examples.
            contribution_guidelines: Score for the contribution guidelines.
            license_specified: Score for license specification.
            badges_present: Score for presence of badges.
    
        Methods:
            evaluate_readme: Evaluates the README file and updates all attribute scores.
            calculate_total_score: Computes the total score from all attributes.
            generate_report: Generates a detailed report of the evaluation.
    """

    readme_quality: Annotated[str, "Assessment of the README quality with a brief comment"] = "Unknown"
    project_description: YesNoPartial = YesNoPartial.UNKNOWN
    installation: YesNoPartial = YesNoPartial.UNKNOWN
    usage_examples: YesNoPartial = YesNoPartial.UNKNOWN
    contribution_guidelines: YesNoPartial = YesNoPartial.UNKNOWN
    license_specified: YesNoPartial = YesNoPartial.UNKNOWN
    badges_present: YesNoPartial = YesNoPartial.UNKNOWN


class CodeDocumentation(BaseModel):
    """
    A class for evaluating the quality of code documentation in a repository.
    
        Class Attributes:
        - tests_present: Indicates whether tests are present in the documentation.
        - docs_quality: Represents the overall quality of the documentation.
        - outdated_content: Indicates if the documentation contains outdated information.
    
        Methods:
        - __init__: Initializes the CodeDocumentation instance with documentation attributes.
        - evaluate_docs: Evaluates the documentation based on various quality metrics.
        - generate_report: Generates a report summarizing the documentation evaluation.
    
        Attributes:
        - tests_present: A boolean indicating the presence of tests in the documentation.
        - docs_quality: A string representing the quality level of the documentation.
        - outdated_content: A boolean indicating if the documentation is outdated.
    
        The class provides methods to assess and report on the state of code documentation, helping to identify areas for improvement.
    """

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
    """
    OverallAssessment class provides a structured evaluation of a codebase by identifying key issues and suggesting improvements.
    
        This class encapsulates the results of a codebase analysis, storing both identified problems and actionable recommendations for enhancement.
    
        Attributes:
            key_shortcomings: A list of the most significant issues or deficiencies found in the codebase.
            recommendations: A list of suggested improvements or best practices to address the identified shortcomings.
    
        The class organizes assessment findings into clear categories, making it easy to generate comprehensive evaluation reports and track remediation progress.
    """

    key_shortcomings: Annotated[
        list[str],
        "List of the most significant and critical issues that need to be addressed",
    ] = ["There are no critical issues"]
    recommendations: Annotated[
        list[str],
        "Specific improvements to address issues or optimize the process",
    ] = ["No recommendations"]


class RepositoryReport(BaseModel):
    """
    RepositoryReport encapsulates the analysis results of an open-source repository.
    
        This class aggregates various aspects of repository analysis into a structured report,
        including its file structure, README content, documentation quality, and an overall
        assessment. It provides methods to generate, display, and export these reports.
    
        Attributes:
            structure: A summary or representation of the repository's file and directory structure.
            readme: The content and analysis of the repository's README file(s).
            documentation: An evaluation of the repository's inline and external documentation.
            assessment: The overall quality and health assessment of the repository.
    
        Methods:
            generate_report: Compiles the analysis data into a comprehensive report.
            display_report: Outputs the report in a human-readable format to the console.
            export_report: Saves the report to a file in a specified format (e.g., JSON, Markdown).
    """

    structure: RepositoryStructure = RepositoryStructure()
    readme: ReadmeEvaluation = ReadmeEvaluation()
    documentation: CodeDocumentation = CodeDocumentation()
    assessment: OverallAssessment = OverallAssessment()

    class Config:
        extra = "ignore"


class AfterReportBlock(BaseModel):
    """
    AfterReportBlock is a class that handles post-report processing tasks.
    
        This class manages the execution of tasks that need to be performed after
        a report has been generated, such as cleanup operations, notifications,
        or data aggregation.
    
        Attributes:
            name: The identifier for this report block instance.
            description: A brief explanation of what this block does.
            tasks: A collection of tasks to be executed after report generation.
    
        Methods:
            execute: Runs all post-report tasks in sequence.
            add_task: Appends a new task to the task list.
            clear_tasks: Removes all tasks from the task list.
    """

    name: str
    description: str
    tasks: list[tuple[str, bool]]


class AfterReport(BaseModel):
    """
    AfterReport is a class designed to handle post-processing tasks after generating a report. It provides methods for finalizing report data, formatting output, and managing report-related resources.
    
        Methods:
        - finalize_report: Completes the report generation process.
        - format_output: Formats the report data for presentation.
        - manage_resources: Handles cleanup and resource management after report generation.
    
        Attributes:
        - report_data: Stores the generated report content.
        - output_format: Specifies the format for the final report output.
        - resources: Manages external resources used during report processing.
    
        The finalize_report method ensures all data is correctly compiled and validated. The format_output method adjusts the report's layout and style according to specified preferences. The manage_resources method releases or archives any resources tied to the report process. The report_data attribute holds the core content of the report, output_format dictates how the report is presented, and resources tracks any auxiliary items used in report creation.
    """

    summary: str
    blocks: list[AfterReportBlock]


class AfterReportSummary(BaseModel):
    """
    Structured output for after-report summary generation.
    """


    summary: str


class AfterReportBlockPlan(BaseModel):
    """
    Block definition returned by the LLM for structuring the final report.
    
        tasks: list of task names (as shown in the input), not indices.
    """


    name: str
    description: str
    tasks: list[str]


class AfterReportBlocksPlan(RootModel):
    """
    Structured output for after-report block grouping.
    """


    root: list[AfterReportBlockPlan]
