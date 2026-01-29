import argparse
import asyncio
import os
import sys
import time

from pydantic import ValidationError

from osa_tool.config.settings import ConfigLoader, GitSettings
from osa_tool.conversion.notebook_converter import NotebookConverter
from osa_tool.core.git.git_agent import GitHubAgent, GitLabAgent, GitverseAgent, GitAgent
from osa_tool.operations.analysis.repository_report.report_maker import ReportGenerator, WhatHasBeenDoneReportGenerator
from osa_tool.operations.codebase.directory_translation.dirs_and_files_translator import RepositoryStructureTranslator
from osa_tool.operations.codebase.docstring_generation.docstring_generation import DocstringsGenerator
from osa_tool.operations.codebase.requirements_generation.requirements_generation import RequirementsGenerator
from osa_tool.operations.docs.about_generation.about_generator import AboutGenerator
from osa_tool.operations.docs.community_docs_generation.docs_run import generate_documentation
from osa_tool.operations.docs.community_docs_generation.license_generation import LicenseCompiler
from osa_tool.operations.docs.readme_generation.readme_core import ReadmeAgent
from osa_tool.operations.docs.readme_generation.utils import format_time
from osa_tool.operations.docs.readme_translation.readme_translator import ReadmeTranslator
from osa_tool.organization.repo_organizer import RepoOrganizer
from osa_tool.scheduler.scheduler import ModeScheduler
from osa_tool.scheduler.todo_list import ToDoList
from osa_tool.scheduler.workflow_manager import (
    GitHubWorkflowManager,
    GitLabWorkflowManager,
    GitverseWorkflowManager,
    WorkflowManager,
)
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import logger, setup_logging
from osa_tool.utils.utils import (
    delete_repository,
    osa_project_root,
    parse_folder_name,
    rich_section,
    switch_to_output_directory,
)
from osa_tool.validation.doc_validator import DocValidator
from osa_tool.validation.paper_validator import PaperValidator
from osa_tool.validation.report_generator import (
    ReportGenerator as ValidationReportGenerator,
)


def main():
    """Main function to generate a README.md file for a Git repository.

    Handles command-line arguments, clones the repository, creates and checks out a branch,
    generates the README.md file, and commits and pushes the changes.
    """

    # Create a command line argument parser
    parser = build_parser_from_yaml(extra_sections=["settings", "arguments", "workflow"])
    args = parser.parse_args()
    create_fork = not args.no_fork
    create_pull_request = not args.no_pull_request

    # Initialize logging
    logs_dir = os.path.join(os.path.dirname(osa_project_root()), "logs")
    repo_name = parse_folder_name(args.repository)
    setup_logging(repo_name, logs_dir)

    start_time = time.time()
    try:
        # Switch to output directory if present
        if args.output:
            switch_to_output_directory(args.output)

        # Load configurations and update
        config_loader = load_configuration(args)

        # Initialize Git agent and Workflow Manager for used platform, perform operations
        git_agent, workflow_manager = initialize_git_platform(args)

        if create_fork:
            git_agent.star_repository()
            git_agent.create_fork()
        git_agent.clone_repository()

        # Initialize ModeScheduler
        sourcerank = SourceRank(config_loader)
        scheduler = ModeScheduler(config_loader, sourcerank, args, workflow_manager, git_agent.metadata)
        plan = scheduler.plan
        what_has_been_done = ToDoList(scheduler.plan)

        if create_fork:
            git_agent.create_and_checkout_branch()

        # Repository Analysis Report generation
        # NOTE: Must run first - switches GitHub branches
        if plan.get("report"):
            rich_section("Report generation")
            analytics = ReportGenerator(config_loader, git_agent.metadata)
            analytics.build_pdf()
            if create_fork:
                git_agent.upload_report(analytics.filename, analytics.output_path)
            what_has_been_done.mark_did("report")

        # NOTE: Must run first - switches GitHub branches
        if plan.get("validate_doc"):
            rich_section("Document validation")
            content = asyncio.run((DocValidator(config_loader).validate(plan.get("attachment"))))
            if content:
                va_re_gen = ValidationReportGenerator(config_loader, git_agent.metadata)
                va_re_gen.build_pdf("Document", content)
                if create_fork:
                    git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                what_has_been_done.mark_did("validate_doc")
            else:
                logger.warning("Document validation returned no content. Skipping report generation.")
        # NOTE: Must run first - switches GitHub branches
        if plan.get("validate_paper"):
            rich_section("Paper validation")
            content = asyncio.run((PaperValidator(config_loader).validate(plan.get("attachment"))))
            if content:
                va_re_gen = ValidationReportGenerator(config_loader, git_agent.metadata)
                va_re_gen.build_pdf("Paper", content)
                if create_fork:
                    git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                what_has_been_done.mark_did("validate_paper")
            else:
                logger.warning("Paper validation returned no content. Skipping report generation.")

        # .ipynb to .py conversion
        if notebook := plan.get("convert_notebooks"):
            rich_section("Jupyter notebooks conversion")
            convert_notebooks(args.repository, notebook)
            what_has_been_done.mark_did("convert_notebooks")

        # Auto translating names of directories
        if plan.get("translate_dirs"):
            rich_section("Directory and file translation")
            translation = RepositoryStructureTranslator(config_loader)
            translation.rename_directories_and_files()
            what_has_been_done.mark_did("translate_dirs")

        # Docstring generation
        if plan.get("docstring"):
            rich_section("Docstrings generation")
            DocstringsGenerator(config_loader, args.ignore_list).run()
            what_has_been_done.mark_did("docstring")

        # License compiling
        if license_type := plan.get("ensure_license"):
            rich_section("License generation")
            LicenseCompiler(config_loader, git_agent.metadata, license_type).run()
            what_has_been_done.mark_did("ensure_license")

        # Generate community documentation
        if plan.get("community_docs"):
            rich_section("Community docs generation")
            generate_documentation(config_loader, git_agent.metadata)
            what_has_been_done.mark_did("community_docs")

        # Requirements generation
        if plan.get("requirements"):
            rich_section("Requirements generation")
            RequirementsGenerator(config_loader).generate()
            what_has_been_done.mark_did("requirements")

        # Readme generation
        if plan.get("readme"):
            rich_section("README generation")
            readme_agent = ReadmeAgent(
                config_loader, git_agent.metadata, plan.get("attachment"), plan.get("refine_readme")
            )
            readme_agent.generate_readme()
            what_has_been_done.mark_did("readme")

        # Readme translation
        translate_readme = plan.get("translate_readme")
        if translate_readme:
            rich_section("README translation")
            ReadmeTranslator(config_loader, git_agent.metadata, translate_readme).translate_readme()
            what_has_been_done.mark_did("translate_readme")

        # About section generation
        about_gen = None
        if plan.get("about"):
            rich_section("About Section generation")
            about_gen = AboutGenerator(config_loader, git_agent)
            about_gen.generate_about_content()
            if create_fork:
                git_agent.update_about_section(about_gen.get_about_content())
            if not create_pull_request:
                logger.info("About section:\n" + about_gen.get_about_section_message())
            what_has_been_done.mark_did("about")

        # Generate platform-specified CI/CD files
        if plan.get("generate_workflows"):
            rich_section("Workflows generation")
            workflow_manager.update_workflow_config(config_loader, plan)
            workflow_manager.generate_workflow(config_loader)
            what_has_been_done.mark_did("generate_workflows")

        # Organize repository by adding 'tests' and 'examples' directories if they aren't exist
        if plan.get("organize"):
            rich_section("Repository organization")
            organizer = RepoOrganizer(os.path.join(os.getcwd(), parse_folder_name(args.repository)))
            organizer.organize()
            what_has_been_done.mark_did("organize")

        if create_fork and create_pull_request:
            rich_section("Publishing changes")
            changes = git_agent.commit_and_push_changes(force=True)
            git_agent.create_pull_request(
                body=about_gen.get_about_section_message() if about_gen else "", changes=changes
            )

        if plan.get("delete_dir"):
            rich_section("Repository deletion")
            delete_repository(args.repository)
            what_has_been_done.mark_did("delete_dir")

        WhatHasBeenDoneReportGenerator(
            config_loader, what_has_been_done.list_for_report, git_agent.metadata
        ).build_pdf()

        elapsed_time = time.time() - start_time
        rich_section(f"All operations completed successfully in total time: {format_time(elapsed_time)}")
        sys.exit(0)

    except Exception as e:
        logger.error("Error: %s", e, exc_info=False if args.web_mode else True)
        sys.exit(1)


def initialize_git_platform(args) -> tuple[GitAgent, WorkflowManager]:
    if "github.com" in args.repository:
        git_agent = GitHubAgent(args.repository, args.branch, author=args.author)
        workflow_manager = GitHubWorkflowManager(args.repository, git_agent.metadata, args)
    elif "gitlab." in args.repository:
        git_agent = GitLabAgent(args.repository, args.branch, author=args.author)
        workflow_manager = GitLabWorkflowManager(args.repository, git_agent.metadata, args)
    elif "gitverse.ru" in args.repository:
        git_agent = GitverseAgent(args.repository, args.branch, author=args.author)
        workflow_manager = GitverseWorkflowManager(args.repository, git_agent.metadata, args)
    else:
        raise ValueError(f"Cannot initialize Git Agent and Workflow Manager for this platform: {args.repository}")

    return git_agent, workflow_manager


def convert_notebooks(repo_url: str, notebook_paths: list[str] | None = None) -> None:
    """Converts Jupyter notebooks to Python scripts based on provided paths.

    Args:
        repo_url: Repository url.
        notebook_paths: A list of paths to the notebooks to be converted (or None).
                        If empty, the converter will process the current repository.
    """
    try:
        converter = NotebookConverter()
        if len(notebook_paths) == 0:
            converter.process_path(os.path.basename(repo_url))
        else:
            for path in notebook_paths:
                converter.process_path(path)

    except Exception as e:
        logger.error("Error while converting notebooks: %s", repr(e), exc_info=True)


def load_configuration(args: argparse.Namespace) -> ConfigLoader:
    """
    Load and update the osa_tool configuration using command-line arguments.

    This function takes the parsed command-line arguments (argparse.Namespace)
    generated from `build_parser_from_yaml` and updates the global configuration
    object (`ConfigLoader`) accordingly.

    It validates the provided repository URL via `GitSettings` and applies all
    LLM-related settings such as model name, API provider, temperature, max tokens,
    and other model parameters.

    Args:
        args (argparse.Namespace):
            Parsed arguments returned by `parser.parse_args()`. It must contain:
                - args.repository    : URL of the repository to analyze
                - args.api           : LLM API provider name
                - args.base_url      : Base URL of an OpenAI-compatible API
                - args.model         : LLM model name
                - args.temperature   : Sampling temperature
                - args.max_tokens    : Maximum number of output tokens
                - args.context_window: Total context window size
                - args.top_p         : Nucleus sampling parameter
                - args.max_retries   : Maximum retry attempts for LLM API calls

    Returns:
        ConfigLoader:
            The updated configuration object ready to be used by osa_tool.

    Raises:
        ValueError:
            If the repository URL fails validation inside `GitSettings`.
    """
    config_loader = ConfigLoader()

    try:
        config_loader.config.git = GitSettings(repository=args.repository)
    except ValidationError as es:
        first_error = es.errors()[0]
        logger.error(f"Value error, Provided URL is not correct: {first_error['input']}")
        sys.exit(1)
    config_loader.config.llm = config_loader.config.llm.model_copy(
        update={
            "api": args.api,
            "base_url": args.base_url,
            "model": args.model,
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
            "context_window": args.context_window,
            "top_p": args.top_p,
            "max_retries": args.max_retries,
        }
    )
    logger.info("Config successfully updated and loaded")
    return config_loader


if __name__ == "__main__":
    main()
