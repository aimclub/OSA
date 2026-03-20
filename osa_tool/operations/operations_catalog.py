import inspect
import os
from typing import List, Literal

from pydantic import BaseModel, Field

from osa_tool.operations.analysis.repository_report.report_maker import ReportGenerator
from osa_tool.operations.analysis.repository_validation.doc_validator import DocValidator
from osa_tool.operations.analysis.repository_validation.paper_validator import PaperValidator
from osa_tool.operations.codebase.directory_translation.dirs_and_files_translator import RepositoryStructureTranslator
from osa_tool.operations.codebase.docstring_generation.docstring_generation import DocstringsGenerator
from osa_tool.operations.codebase.notebook_conversion.notebook_converter import NotebookConverter
from osa_tool.operations.codebase.organization.repo_organizer import RepoOrganizer
from osa_tool.operations.codebase.requirements_generation.requirements_generation import RequirementsGenerator
from osa_tool.operations.codebase.workflow_generation.workflow_executor import WorkflowsExecutor
from osa_tool.operations.docs.about_generation.about_generator import AboutGenerator
from osa_tool.operations.docs.community_docs_generation.docs_run import generate_documentation
from osa_tool.operations.docs.community_docs_generation.license_generation import LicenseCompiler
from osa_tool.operations.docs.readme_generation.readme_core import ReadmeAgent
from osa_tool.operations.docs.readme_translation.readme_translator import ReadmeTranslator
from osa_tool.operations.registry import Operation, OperationRegistry
from osa_tool.utils.utils import osa_project_root


class GenerateReportOperation(Operation):
    """
    This class represents an operation for generating reports.
    
        Methods:
        - __init__: Initializes the GenerateReportOperation instance.
        - execute: Executes the report generation operation.
        - validate: Validates the operation's parameters and dependencies.
        - prepare: Prepares the necessary data and environment for report generation.
        - cleanup: Cleans up resources after report generation.
    
        Attributes:
        - name: The name of the operation.
        - description: A description of what the operation does.
        - supported_intents: The intents that this operation supports.
        - supported_scopes: The scopes in which this operation can be used.
        - priority: The priority level of the operation.
        - executor: The executor responsible for running the operation.
        - ReportGenerator: The report generator instance used by the operation.
        - executor_method: The specific method of the executor to call.
        - executor_dependencies: Dependencies required by the executor.
    
        The class encapsulates the logic for generating reports, including validation, preparation, execution, and cleanup. It uses a ReportGenerator to create reports based on provided parameters and ensures all dependencies are satisfied before execution.
    """

    name = "generate_report"
    description = "Generate repository quality report as PDF"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "analysis"]
    priority = 5

    executor = ReportGenerator
    executor_method = "run"
    executor_dependencies = ["config_manager", "git_agent", "create_fork"]


class DocValidationOperation(Operation):
    """
    Validates document content against specified rules and intents.
    
            This class encapsulates a document validation operation, defining the rules,
            intents, and execution logic for validating documents. It manages dependencies
            and state required for the validation process.
    
            Attributes:
                name (str): The unique identifier for the validation operation.
                description (str): A brief description of what the validation operation does.
                supported_intents (list): List of intents that this operation can validate against.
                supported_scopes (list): List of scopes (e.g., document sections) where validation applies.
                priority (int): The priority level of this operation relative to others.
                executor (callable): The function or method that executes the validation logic.
                DocValidator (class): The validator class used for performing the validation.
                executor_method (str): The name of the method within DocValidator to call for execution.
                executor_dependencies (list): Dependencies required by the executor for operation.
                state_dependencies (list): State variables or data needed from the document context.
    
            Methods:
                execute: Runs the validation operation using the configured executor and dependencies.
                validate: Checks if the operation is applicable to the given document and intent.
                get_dependencies: Retrieves the list of dependencies required for execution.
    """

    name = "validate_doc"
    description = (
        "Check if the procedures or workflows from the attached technical documentation "
        "can be reproduced using the selected repository."
    )

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "analysis"]
    priority = 10

    executor = DocValidator
    executor_method = "run"
    executor_dependencies = ["config_manager", "git_agent", "create_fork"]
    state_dependencies = ["attachment"]


class PaperValidationOperation(Operation):
    """
    PaperValidationOperation is a class that defines an operation for validating academic papers, typically used within a larger workflow or pipeline system.
    
        Class Attributes:
        - name: The identifier for the operation.
        - description: A brief explanation of what the operation does.
        - supported_intents: The types of intents this operation can handle.
        - supported_scopes: The contexts or scopes in which the operation is applicable.
        - priority: The execution priority level of the operation.
        - executor: The component responsible for executing the validation logic.
        - PaperValidator: The validator instance used to perform paper validation checks.
        - executor_method: The specific method on the executor that runs the validation.
        - executor_dependencies: Dependencies required by the executor to function.
        - state_dependencies: State information or data that the operation relies on.
    
        These attributes collectively configure the operation's behavior, dependencies, and integration within a validation workflow, ensuring it validates papers according to specified intents and scopes.
    """

    name = "validate_paper"
    description = (
        "Check if the experiments and methodology from the attached research paper "
        "can be reproduced using the selected repository."
    )

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "analysis"]
    priority = 15

    executor = PaperValidator
    executor_method = "run"
    executor_dependencies = ["config_manager", "git_agent", "create_fork"]
    state_dependencies = ["attachment"]


class ConvertNotebooksArgs(BaseModel):
    """
    Converts Jupyter notebooks to other formats based on provided arguments.
    
        Class Attributes:
        - notebook_paths: List of paths to the Jupyter notebooks to be converted.
    
        This class encapsulates the configuration and parameters needed for batch conversion of Jupyter notebooks. It primarily serves as a data container for specifying input notebooks and conversion settings, facilitating organized parameter passing in conversion workflows.
    """

    notebook_paths: List[str] = Field(
        default_factory=list,
        description=(
            "Optional list of .ipynb files or directories to convert. "
            "Example: ['notebooks/analysis.ipynb', 'research/']"
        ),
    )


class ConvertNotebooksOperation(Operation):
    """
    A class that converts Jupyter notebooks to other formats.
    
        Methods:
        - __init__: Initializes the ConvertNotebooksOperation with the given arguments.
        - execute: Executes the notebook conversion operation.
    
        Attributes:
        - name: The name of the operation.
        - description: A description of what the operation does.
        - supported_intents: The intents this operation supports.
        - supported_scopes: The scopes in which this operation can be used.
        - priority: The priority level of the operation.
        - args_schema: The schema for validating operation arguments.
        - ConvertNotebooksArgs: The arguments specific to notebook conversion.
        - args_policy: The policy for handling arguments.
        - executor: The executor responsible for running the conversion.
        - NotebookConverter: The converter used to transform notebooks.
        - executor_method: The method on the executor to call for conversion.
        - executor_dependencies: Dependencies required by the executor.
    
        The __init__ method sets up the operation with necessary configurations and dependencies. The execute method performs the actual conversion of notebooks using the specified executor and converter.
    """

    name = "convert_notebooks"
    description = "Convert Jupyter notebooks (.ipynb) into Python scripts with cleaned code."

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 30

    args_schema = ConvertNotebooksArgs
    args_policy = "auto"

    executor = NotebookConverter
    executor_method = "convert_notebooks"
    executor_dependencies = ["config_manager"]


class TranslateRepositoryStructureOperation(Operation):
    """
    TranslateRepositoryStructureOperation is an operation that translates repository structure into a different format or representation.
    
        This class provides methods to execute the translation operation and manage its lifecycle.
    
        Attributes:
            name: The name of the operation.
            description: A description of what the operation does.
            supported_intents: The intents this operation supports.
            supported_scopes: The scopes this operation can be applied to.
            priority: The priority level of the operation.
            executor: The executor responsible for running the operation.
            RepositoryStructureTranslator: The translator component that performs the actual structure translation.
            executor_method: The specific method on the executor to call.
            executor_dependencies: Dependencies required by the executor.
    
        Methods:
            execute: Executes the translation operation on the given repository structure.
            validate: Validates that the operation can be performed on the given input.
            cleanup: Performs any necessary cleanup after execution.
    """

    name = "translate_dirs"
    description = "Translate directories and files into English"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 40

    executor = RepositoryStructureTranslator
    executor_method = "rename_directories_and_files"
    executor_dependencies = ["config_manager"]


class GenerateDocstringsArgs(BaseModel):
    """
    Generates and manages arguments for the docstring generation process.
    
        Attributes:
            ignore_list: A list of file or directory names to ignore during docstring generation.
            target_path: The file or directory path to analyze for generating docstrings.
            write: A flag indicating whether to write the generated docstrings back to the files.
            overwrite: A flag indicating whether to overwrite existing docstrings in the files.
            verbose: A flag controlling the verbosity of the output during the generation process.
    
        This class encapsulates the configuration needed to control how docstrings are generated,
        such as specifying which files to process, whether to save changes, and the level of
        detail in the operation's output.
    """

    ignore_list: List[str] = Field(
        default_factory=list,
        description=(
            "Optional list of directories or files to ignore during docstring generation. "
            "Example: ['tests', 'moduleA/featureB', '__init__.py']"
        ),
    )


class GenerateDocstringsOperation(Operation):
    """
    A class that generates docstrings for Python code.
    
        This class provides functionality to analyze Python source code and generate
        appropriate docstrings for functions, classes, and methods based on their
        signatures and usage patterns.
    
        Attributes:
            name: The name of the operation.
            description: A description of what the operation does.
            supported_intents: The types of intents this operation supports.
            supported_scopes: The code scopes this operation can work with.
            priority: The execution priority of this operation.
            args_schema: The schema for validating operation arguments.
            GenerateDocstringsArgs: The argument class for docstring generation.
            args_policy: The policy for handling arguments.
            executor: The executor responsible for running the operation.
            DocstringsGenerator: The component that generates docstrings.
            executor_method: The method used by the executor.
            executor_dependencies: Dependencies required by the executor.
    
        The class orchestrates the docstring generation process by coordinating
        between argument validation, code analysis, and docstring formatting
        components. Attributes control the operation's behavior and configuration,
        while methods handle the execution flow and integration with the larger
        system.
    """

    name = "generate_docstrings"
    description = "Generate and update docstrings across the codebase"

    supported_intents = ["new_task", "feedback"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 50

    args_schema = GenerateDocstringsArgs
    args_policy = "auto"

    executor = DocstringsGenerator
    executor_method = "run"
    executor_dependencies = ["config_manager"]


class EnsureLicenseArgs(BaseModel):
    """
    Args for ensuring license presence.
    
        Attributes:
            license_type: The type of license to ensure.
    """

    license_type: Literal["bsd-3", "mit", "ap2"] = Field("bsd-3", description="License type to set for the repository.")


class EnsureLicenseOperation(Operation):
    """
    Ensures that a license is present and valid for a given project.
    
        This operation checks for the existence of a license file, validates its content,
        and can generate or update a license if necessary. It is designed to be integrated
        into automated workflows for project compliance.
    
        Class Attributes:
        - name: The unique identifier for this operation.
        - description: A brief explanation of the operation's purpose.
        - supported_intents: The types of project intents this operation can handle.
        - supported_scopes: The project scopes (e.g., file, directory) where the operation applies.
        - priority: The execution priority relative to other operations.
        - args_schema: The schema defining the structure and validation rules for operation arguments.
        - EnsureLicenseArgs: The specific argument class used to configure the license check.
        - args_policy: The policy governing how arguments are processed and validated.
        - executor: The component responsible for carrying out the license verification logic.
        - LicenseCompiler: The utility used to compile or generate license text.
        - executor_method: The specific method on the executor that performs the core operation.
        - executor_dependencies: External dependencies required by the executor to function.
    
        Methods:
        - __init__: Initializes the operation with its configuration and dependencies.
        - execute: Performs the license check and enforcement based on provided arguments.
        - validate_args: Validates the input arguments against the defined schema.
        - get_dependencies: Returns the list of dependencies needed for execution.
    """

    name = "ensure_license"
    description = "Ensure LICENSE file exists"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "docs"]
    priority = 60

    args_schema = EnsureLicenseArgs
    args_policy = "auto"

    executor = LicenseCompiler
    executor_method = "run"
    executor_dependencies = ["config_manager", "metadata"]


class GenerateCommunityDocsOperation(Operation):
    """
    Generates community documentation for a given repository.
    
        This class is designed to automate the creation of community-focused documentation,
        such as contribution guidelines, code of conduct, and other community-related files,
        based on the repository's structure and content.
    
        Class Attributes:
        - name: The name of the operation.
        - description: A brief description of what the operation does.
        - supported_intents: The intents this operation supports.
        - supported_scopes: The scopes within which this operation can be applied.
        - priority: The priority level of the operation.
        - executor: The executor responsible for running the operation.
        - executor_method: The specific method of the executor to call.
        - executor_dependencies: Dependencies required by the executor.
    
        These attributes collectively define the operation's identity, behavior, and execution context,
        enabling it to be properly configured and integrated within a larger documentation generation system.
    """

    name = "generate_documentation"
    description = "Generate additional documentation files (e.g., CONTRIBUTING, CODE_OF_CONDUCT)."

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "docs"]
    priority = 65

    executor = staticmethod(generate_documentation)
    executor_method = None
    executor_dependencies = ["config_manager", "metadata"]


class RequirementsGeneratorOperation(Operation):
    """
    This class represents an operation that generates requirements for a given context.
    
        Methods:
        - __init__: Initializes the RequirementsGeneratorOperation with the provided parameters.
        - execute: Executes the operation to generate requirements based on the given context.
    
        Attributes:
        - name: The name of the operation.
        - description: A description of what the operation does.
        - supported_intents: The intents that this operation supports.
        - supported_scopes: The scopes in which this operation can be applied.
        - priority: The priority level of the operation.
        - executor: The executor responsible for running the operation.
        - RequirementsGenerator: The generator used to create requirements.
        - executor_method: The specific method of the executor to call.
        - executor_dependencies: Dependencies required by the executor.
    
        The __init__ method sets up the operation's configuration, while the execute method performs the actual requirement generation using the specified executor and generator.
    """

    name = "generate_requirements"
    description = "Generate requirements.txt using pipreqs"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 67

    executor = RequirementsGenerator
    executor_method = "generate"
    executor_dependencies = ["config_manager"]


class GenerateReadmeOperation(Operation):
    """
    A class that generates a README file for a given repository.
    
        Methods:
        - __init__: Initializes the GenerateReadmeOperation with necessary dependencies.
        - execute: Executes the README generation process.
    
        Attributes:
        - name: The name of the operation.
        - description: A description of what the operation does.
        - supported_intents: The intents that this operation supports.
        - supported_scopes: The scopes in which this operation can be applied.
        - priority: The priority level of the operation.
        - executor: The executor responsible for running the operation.
        - ReadmeAgent: The agent that handles README generation logic.
        - executor_method: The specific method of the executor to call.
        - executor_dependencies: Dependencies required by the executor.
        - state_dependencies: Dependencies related to the operation's state.
    
        The __init__ method sets up the operation with its name, description, supported intents and scopes, priority, executor, ReadmeAgent, executor method, and dependencies. The execute method runs the README generation using the configured executor and agent, handling the repository data to produce a README file.
    """

    name = "generate_readme"
    description = "Generate or improve README.md for the repository"

    supported_intents = ["new_task", "feedback"]
    supported_scopes = ["full_repo", "docs"]
    priority = 70

    executor = ReadmeAgent
    executor_method = "generate_readme"
    executor_dependencies = ["config_manager", "metadata"]
    state_dependencies = ["attachment"]


class TranslateReadmeArgs(BaseModel):
    """
    TranslateReadmeArgs is a class that holds configuration arguments for translating README files.
    
        Attributes:
        - languages: A list of target languages for translation.
    
        This class encapsulates the necessary parameters to specify which languages a README should be translated into, facilitating the translation process by grouping related configuration data.
    """

    languages: List[str] = Field(
        ...,
        description="List of languages to translate README.md into. Example: ['Russian', 'Swedish']",
    )


class TranslateReadmeOperation(Operation):
    """
    TranslateReadmeOperation is an operation class that translates README files from one language to another using a specified translator.
    
        Class Attributes:
        - name: The name of the operation.
        - description: A brief description of what the operation does.
        - supported_intents: The intents that this operation supports.
        - supported_scopes: The scopes in which this operation can be executed.
        - priority: The priority level of the operation.
        - args_schema: The schema for validating operation arguments.
        - TranslateReadmeArgs: The argument class used by this operation.
        - args_policy: The policy for handling arguments.
        - executor: The executor responsible for running the operation.
        - ReadmeTranslator: The translator used for translating README files.
        - executor_method: The method of the executor that performs the translation.
        - executor_dependencies: Dependencies required by the executor.
    
        These attributes collectively define the operation's behavior, configuration, and dependencies for translating README files.
    """

    name = "translate_readme"
    description = "Translate README.md into another language"

    supported_intents = ["new_task", "feedback"]
    supported_scopes = ["full_repo", "docs"]
    priority = 75

    args_schema = TranslateReadmeArgs
    args_policy = "ask_if_missing"

    executor = ReadmeTranslator
    executor_method = "translate_readme"
    executor_dependencies = ["config_manager", "metadata"]


class GenerateAboutOperation(Operation):
    """
    Generates an 'About' operation for the application.
    
        This class is responsible for creating an operation that provides information
        about the application, such as its version, description, and other metadata.
        It configures the operation with specific intents, scopes, and dependencies
        required for execution.
    
        Attributes:
            name: The name of the operation.
            description: A brief description of what the operation does.
            supported_intents: The intents that this operation supports.
            supported_scopes: The scopes within which this operation can be executed.
            priority: The priority level of the operation.
            executor: The executor responsible for running the operation.
            AboutGenerator: The generator used to create the 'About' content.
            executor_method: The specific method of the executor to be called.
            executor_dependencies: Dependencies required by the executor to run the operation.
    
        Methods:
            __init__: Initializes the GenerateAboutOperation with the provided configuration.
            execute: Executes the 'About' operation and returns the generated content.
    """

    name = "generate_about"
    description = "Generate About section with tags."

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "docs"]
    priority = 80

    executor = AboutGenerator
    executor_method = "generate_about_content"
    executor_dependencies = ["config_manager", "git_agent"]


class GenerateWorkflowsArgs(BaseModel):
    """
    Class for generating GitHub Actions workflow configurations.
    
        Attributes:
        - include_black: Whether to include Black code formatting workflow.
        - include_tests: Whether to include test execution workflow.
        - include_pep8: Whether to include PEP8 style checking workflow.
        - include_autopep8: Whether to include autopep8 automatic PEP8 fixing workflow.
        - include_fix_pep8: Whether to include manual PEP8 fixing workflow.
        - include_pypi: Whether to include PyPI publishing workflow.
        - pep8_tool: Tool to use for PEP8 checking (e.g., flake8, pycodestyle).
        - use_poetry: Whether to use Poetry for dependency management.
        - include_codecov: Whether to include Codecov integration for coverage reporting.
        - python_versions: List of Python versions to test against.
        - branches: List of git branches to trigger workflows on.
    
        These attributes control which workflows are generated and their configuration parameters, allowing customization of CI/CD pipelines for Python projects.
    """

    include_black: bool = Field(True, description="Generate Black code formatter workflow.")
    include_tests: bool = Field(True, description="Generate unit tests workflow.")
    include_pep8: bool = Field(True, description="Generate PEP 8 compliance check workflow.")
    include_autopep8: bool = Field(False, description="Generate autopep8 auto-fix workflow.")
    include_fix_pep8: bool = Field(False, description="Generate fix-pep8 slash-command workflow.")
    include_pypi: bool = Field(False, description="Generate PyPI publish workflow.")
    pep8_tool: Literal["flake8", "pylint"] = Field("flake8", description="Tool for PEP 8 checking.")
    use_poetry: bool = Field(False, description="Use Poetry for PyPI packaging.")
    include_codecov: bool = Field(True, description="Include Codecov coverage upload step.")
    python_versions: List[str] = Field(
        default_factory=lambda: ["3.9", "3.10"],
        description="Python versions to test against. Example: ['3.10', '3.11', '3.12']",
    )
    branches: List[str] = Field(
        default_factory=lambda: ["main", "master"],
        description="Git branches to trigger workflows on.",
    )


class GenerateWorkflowsOperation(Operation):
    """
    Generates workflows based on provided arguments.
    
        This class is responsible for creating and managing workflows according to the specified parameters and intents. It handles the orchestration of workflow generation logic.
    
        Attributes:
            name: The name of the operation.
            description: A description of what the operation does.
            supported_intents: The intents this operation supports.
            supported_scopes: The scopes within which this operation can be executed.
            priority: The priority level of the operation.
            args_schema: The schema for validating operation arguments.
            GenerateWorkflowsArgs: The class defining the structure of arguments for workflow generation.
            args_policy: The policy governing argument handling and validation.
            executor: The executor responsible for running the workflow generation.
            WorkflowsExecutor: The specific executor class for workflows.
            executor_method: The method on the executor to call for generation.
            executor_dependencies: Dependencies required by the executor.
    """

    name = "generate_workflows"
    description = "Generate CI/CD workflow files (GitHub Actions / GitLab CI) for the repository."

    supported_intents = ["new_task", "feedback"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 85

    args_schema = GenerateWorkflowsArgs
    args_policy = "auto"

    executor = WorkflowsExecutor
    executor_method = "generate"
    executor_dependencies = ["config_manager", "workflow_manager"]


class OrganizeRepositoryOperation(Operation):
    """
    Organizes a repository by applying a series of organizational rules.
    
        This operation class is designed to be executed within a larger system to
        clean up and structure a code repository. It leverages a `RepoOrganizer` to
        apply specific organizational intents and scopes.
    
        Attributes:
            name: The identifier for this operation.
            description: A brief explanation of the operation's purpose.
            supported_intents: The organizational goals this operation can fulfill.
            supported_scopes: The parts of the repository this operation can affect.
            priority: The execution order priority relative to other operations.
            executor: The callable responsible for running the operation's logic.
            RepoOrganizer: The core organizer instance that applies the rules.
            executor_method: The specific method on the executor to be called.
            executor_dependencies: Other operations or resources this operation requires to run.
    
        The attributes collectively define the operation's behavior, configuration,
        and dependencies, enabling it to be dynamically executed within an
        organizational pipeline.
    """

    name = "organize"
    description = (
        "Organize the repository structure by adding standard 'tests' and "
        "'examples' directories if missing and moving matching files."
    )

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 90

    executor = RepoOrganizer
    executor_method = "organize"
    executor_dependencies = ["config_manager"]


def register_all_operations(generate_docs: bool = True):
    """
    Auto-register all Operation subclasses declared in this module and optionally regenerate markdown documentation.
    
    This function scans the current module for any class that is a subclass of Operation (excluding Operation itself) and registers an instance of each with the OperationRegistry. This ensures all available operations are centrally registered and ready for use.
    
    After registration, if documentation generation is enabled, it creates or updates a markdown file listing all registered operations in a table format. The file is saved to a predefined location within the project's documentation directory.
    
    Args:
        generate_docs: If True, automatically generate a markdown documentation file after registration. Defaults to True.
    
    Returns:
        None
    """
    current_module = globals()

    # Register all operations dynamically
    for obj in current_module.values():
        if inspect.isclass(obj) and issubclass(obj, Operation) and obj is not Operation:
            OperationRegistry.register(obj())

    docs_path = os.path.join(os.path.dirname(osa_project_root()), "docs", "core", "operations", "OPERATIONS.md")
    if generate_docs:
        generate_operations_markdown(docs_path)


def generate_operations_markdown(path: str):
    """
    Generates a Markdown file enumerating all registered operations in a table format.
    This file is intended for developers to quickly reference available operations, their priorities, supported intents and scopes, argument schemas, and executor details.
    
    The method retrieves all operations from the OperationRegistry, sorts them by priority, and writes a formatted Markdown table to the specified file path. This auto-generated document should not be edited manually, as it reflects the current state of the operation registry.
    
    Args:
        path: The file system path where the Markdown file will be written.
    
    Returns:
        None
    """
    operations = sorted(OperationRegistry.list_all(), key=lambda operation: operation.priority)

    lines = [
        "# Available Operations",
        "",
        "This document is auto-generated. Do not edit manually.",
        "",
        "---",
        "",
        "| Name | Priority | Intents | Scopes | Args Schema | Executor | Method |",
        "|------|----------|---------|--------|-------------|----------|--------|",
    ]

    for op in operations:
        name = f"`{op.name}`"
        priority = str(op.priority)
        intents = ", ".join(op.supported_intents)
        scopes = ", ".join(op.supported_scopes)
        args_schema = op.args_schema.__name__ if op.args_schema else "—"

        # Executor formatting
        if hasattr(op.executor, "__name__"):
            executor = op.executor.__name__
        else:
            executor = str(op.executor)

        method = op.executor_method or "—"

        lines.append(f"| {name} | {priority} | {intents} | {scopes} | {args_schema} | `{executor}` | `{method}` |")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
