import inspect
import os
from typing import Optional, List, Literal

from pydantic import BaseModel

from osa_tool.operations.analysis.repository_report.report_maker import ReportGenerator
from osa_tool.operations.codebase.directory_translation.dirs_and_files_translator import RepositoryStructureTranslator
from osa_tool.operations.codebase.docstring_generation.docstring_generation import DocstringsGenerator
from osa_tool.operations.codebase.requirements_generation.requirements_generation import RequirementsGenerator
from osa_tool.operations.docs.about_generation.about_generator import AboutGenerator
from osa_tool.operations.docs.community_docs_generation.docs_run import generate_documentation
from osa_tool.operations.docs.community_docs_generation.license_generation import LicenseCompiler
from osa_tool.operations.docs.readme_generation.readme_core import ReadmeAgent
from osa_tool.operations.docs.readme_translation.readme_translator import ReadmeTranslator
from osa_tool.operations.registry import Operation, OperationRegistry
from osa_tool.utils.utils import osa_project_root


class GenerateReportOperation(Operation):
    name = "generate_report"
    description = "Generate repository quality report as PDF"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "analysis"]
    priority = 5

    executor = ReportGenerator
    executor_method = "build_pdf"
    executor_dependencies = ["config_manager", "metadata"]


class TranslateRepositoryStructureOperation(Operation):
    name = "translate_dirs"
    description = "Translate directories and files into English"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 40

    executor = RepositoryStructureTranslator
    executor_method = "rename_directories_and_files"
    executor_dependencies = ["config_manager"]


class GenerateDocstringsArgs(BaseModel):
    ignore_list: List[str] = []


class GenerateDocstringsOperation(Operation):
    name = "generate_docstrings"
    description = "Generate and update docstrings across the codebase"

    supported_intents = ["new_task", "feedback"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 50

    args_schema = GenerateDocstringsArgs
    args_policy = "auto"
    prompt_for_args = (
        "Optional parameter ignore_list: a list of directories or files "
        "to ignore during docstring generation. "
        "Paths must be relative to the project root. "
        "If omitted, only '__init__.py' is ignored.\n\n"
        "Example:\n"
        "{'ignore_list': ['tests', 'moduleA/featureB', '__init__.py']}"
    )

    executor = DocstringsGenerator
    executor_method = "run"
    executor_dependencies = ["config_manager"]


class EnsureLicenseArgs(BaseModel):
    ensure_license: Literal["bsd-3", "mit", "ap2"] = "bsd-3"


class EnsureLicenseOperation(Operation):
    name = "ensure_license"
    description = "Ensure LICENSE file exists"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "docs"]
    priority = 60

    args_schema = EnsureLicenseArgs
    args_policy = "auto"
    prompt_for_args = (
        "For operation 'ensure_license' provide a license type. "
        "Expected key: 'license_type'."
        "Allowed values: 'bsd-3', 'mit', 'ap2'."
        "If not specified, use 'bsd-3'."
    )

    executor = LicenseCompiler
    executor_method = "run"
    executor_dependencies = ["config_manager", "metadata"]


class GenerateCommunityDocsOperation(Operation):
    name = "generate_documentation"
    description = "Generate additional documentation files (e.g., CONTRIBUTING, CODE_OF_CONDUCT)."

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "docs"]
    priority = 65

    executor = staticmethod(generate_documentation)
    executor_method = None
    executor_dependencies = ["config_manager", "metadata"]


class RequirementsGeneratorOperation(Operation):
    name = "generate_requirements"
    description = "Generate requirements.txt using pipreqs"

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "codebase"]
    priority = 67

    executor = RequirementsGenerator
    executor_method = "generate"
    executor_dependencies = ["config_manager"]


class GenerateReadmeArgs(BaseModel):
    article: Optional[str] = None


class GenerateReadmeOperation(Operation):
    name = "generate_readme"
    description = "Generate or improve README.md for the repository"

    supported_intents = ["new_task", "feedback"]
    supported_scopes = ["full_repo", "docs"]
    priority = 70

    args_schema = GenerateReadmeArgs
    args_policy = "auto"
    prompt_for_args = "Provide the content for README.md if you want to override default generation."

    executor = ReadmeAgent
    executor_method = "generate_readme"
    executor_dependencies = ["config_manager", "metadata"]
    state_dependencies = ["attachment"]


class TranslateReadmeArgs(BaseModel):
    languages: List[str]


class TranslateReadmeOperation(Operation):
    name = "translate_readme"
    description = "Translate README.md into another language"

    supported_intents = ["new_task", "feedback"]
    supported_scopes = ["full_repo", "docs"]
    priority = 75

    args_schema = TranslateReadmeArgs
    args_policy = "ask_if_missing"
    prompt_for_args = (
        "For operation 'translate_readme' provide a list of languages " "(e.g., {'languages': ['Russian', 'Swedish']})."
    )

    executor = ReadmeTranslator
    executor_method = "translate_readme"
    executor_dependencies = ["config_manager", "metadata"]


class GenerateAboutOperation(Operation):
    name = "generate_about"
    description = "Generate About section with tags."

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "docs"]
    priority = 80

    executor = AboutGenerator
    executor_method = "generate_about_content"
    executor_dependencies = ["config_manager", "git_agent"]


def register_all_operations(generate_docs: bool = True):
    """
    Auto-register all Operation subclasses declared in this module
    AND optionally regenerate markdown documentation.
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
    Generates a Markdown file enumerating all operations in table format.
    Intended for developers.
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
