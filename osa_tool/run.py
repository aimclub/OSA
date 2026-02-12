import asyncio
import os
import sys
import time

from osa_tool.config.settings import ConfigManager
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
        config_manager = ConfigManager(args)

        # Initialize Git agent and Workflow Manager for used platform, perform operations
        git_agent, workflow_manager = initialize_git_platform(args)

        if create_fork:
            git_agent.star_repository()
            git_agent.create_fork()
        git_agent.clone_repository()

        # Initialize ModeScheduler
        sourcerank = SourceRank(config_manager)
        scheduler = ModeScheduler(config_manager, sourcerank, args, workflow_manager, git_agent.metadata)
        plan = scheduler.plan

        if create_fork:
            git_agent.create_and_checkout_branch()

        # Repository Analysis Report generation
        # NOTE: Must run first - switches GitHub branches
        if plan.get("report"):
            rich_section("Report generation")
            plan.mark_started("report")
            analytics = ReportGenerator(config_manager, git_agent.metadata)
            try:
                analytics.build_pdf()
                if create_fork:
                    git_agent.upload_report(analytics.filename, analytics.output_path)
                plan.mark_done("report")
            except ValueError:
                plan.mark_failed("report")

        # NOTE: Must run first - switches GitHub branches
        if plan.get("validate_doc"):
            plan.mark_started("validate_doc")
            rich_section("Document validation")
            content = asyncio.run((DocValidator(config_manager).validate(plan.get("attachment"))))
            if content:
                va_re_gen = ValidationReportGenerator(config_manager, git_agent.metadata)
                va_re_gen.build_pdf("Document", content)
                if create_fork:
                    git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                plan.mark_done("validate_doc")
            else:
                plan.mark_failed("validate_doc")
                logger.warning("Document validation returned no content. Skipping report generation.")
        # NOTE: Must run first - switches GitHub branches
        if plan.get("validate_paper"):
            plan.mark_started("validate_paper")
            rich_section("Paper validation")
            content = asyncio.run((PaperValidator(config_manager).validate(plan.get("attachment"))))
            if content:
                va_re_gen = ValidationReportGenerator(config_manager, git_agent.metadata)
                va_re_gen.build_pdf("Paper", content)
                if create_fork:
                    git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                plan.mark_done("validate_paper")
            else:
                plan.mark_failed("validate_paper")
                logger.warning("Paper validation returned no content. Skipping report generation.")

        # .ipynb to .py conversion
        if notebook := plan.get("convert_notebooks"):
            plan.mark_started("convert_notebooks")
            rich_section("Jupyter notebooks conversion")
            if convert_notebooks(args.repository, notebook):
                plan.mark_done("convert_notebooks")
            else:
                plan.mark_failed("convert_notebooks")

        # Auto translating names of directories
        if plan.get("translate_dirs"):
            rich_section("Directory and file translation")
            RepositoryStructureTranslator(config_manager, plan).rename_directories_and_files()

        # Docstring generation
        if plan.get("docstring"):
            rich_section("Docstrings generation")
            DocstringsGenerator(config_manager, args.ignore_list, plan).run()

        # License compiling
        if plan.get("ensure_license"):
            rich_section("License generation")
            LicenseCompiler(config_manager, git_agent.metadata, plan).run()

        # Generate community documentation
        if plan.get("community_docs"):
            rich_section("Community docs generation")
            generate_documentation(config_manager, git_agent.metadata, plan)

        # Requirements generation
        if plan.get("requirements"):
            rich_section("Requirements generation")
            RequirementsGenerator(config_manager, plan).generate()

        # Readme generation
        if plan.get("readme"):
            rich_section("README generation")
            readme_agent = ReadmeAgent(config_manager, git_agent.metadata, plan)
            readme_agent.generate_readme()

        # Readme translation
        translate_readme = plan.get("translate_readme")
        if translate_readme:
            rich_section("README translation")
            ReadmeTranslator(config_manager, git_agent.metadata, plan).translate_readme()
        # About section generation
        about_gen = None
        if plan.get("about"):
            rich_section("About Section generation")
            about_gen = AboutGenerator(config_manager, git_agent, plan)
            if about_gen.generate_about_content():
                plan.mark_done("about")
            else:
                plan.mark_failed("about")
            if create_fork:
                git_agent.update_about_section(about_gen.get_about_content())
            if not create_pull_request:
                logger.info("About section:\n" + about_gen.get_about_section_message())

        # Generate platform-specified CI/CD files
        if plan.get("generate_workflows"):
            rich_section("Workflows generation")
            plan.mark_started("generate_workflows")
            workflow_manager.update_workflow_config(config_manager, plan)
            if workflow_manager.generate_workflow(config_manager):
                plan.mark_done("generate_workflows")
            else:
                plan.mark_failed("generate_workflows")

        # Organize repository by adding 'tests' and 'examples' directories if they aren't exist
        if plan.get("organize"):
            rich_section("Repository organization")
            plan.mark_started("organize")
            organizer = RepoOrganizer(os.path.join(os.getcwd(), parse_folder_name(args.repository)))
            organizer.organize()
            plan.mark_done("organize")

        if create_fork and create_pull_request:
            rich_section("Publishing changes")
            changes = git_agent.commit_and_push_changes(force=True)
            git_agent.create_pull_request(
                body=about_gen.get_about_section_message() if about_gen else "", changes=changes
            )

        if plan.get("delete_dir"):
            rich_section("Repository deletion")
            plan.mark_started("delete_dir")
            delete_repository(args.repository)
            plan.mark_done("delete_dir")

        if plan.get("report"):
            WhatHasBeenDoneReportGenerator(config_manager, plan.list_for_report, git_agent.metadata).build_pdf()

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


def convert_notebooks(repo_url: str, notebook_paths: list[str] | None = None) -> bool:
    """Converts Jupyter notebooks to Python scripts based on provided paths.

    Args:
        repo_url: Repository url.
        notebook_paths: A list of paths to the notebooks to be converted (or None).
                        If empty, the converter will process the current repository.
    Returns:
        Has the task been completed successfully
    """
    try:
        converter = NotebookConverter()
        if len(notebook_paths) == 0:
            converter.process_path(os.path.basename(repo_url))
        else:
            for path in notebook_paths:
                converter.process_path(path)
        return True
    except Exception as e:
        logger.error("Error while converting notebooks: %s", repr(e), exc_info=True)
    return False


if __name__ == "__main__":
    main()
