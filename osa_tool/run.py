import argparse
import asyncio
import multiprocessing
import os
import subprocess
import sys
import time
from pathlib import Path

from pydantic import ValidationError

from osa_tool.aboutgen.about_generator import AboutGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader, GitSettings
from osa_tool.conversion.notebook_converter import NotebookConverter
from osa_tool.git_agent.git_agent import GitHubAgent, GitLabAgent, GitverseAgent, GitAgent
from osa_tool.operations.analysis.repository_report.report_maker import ReportGenerator, WhatHasBeenDoneReportGenerator
from osa_tool.operations.docs.community_docs_generation.docs_run import generate_documentation
from osa_tool.operations.docs.community_docs_generation.license_generation import LicenseCompiler
from osa_tool.operations.docs.readme_generation.readme_core import ReadmeAgent
from osa_tool.operations.docs.readme_generation.utils import format_time
from osa_tool.operations.docs.readme_translation.readme_translator import ReadmeTranslator
from osa_tool.organization.repo_organizer import RepoOrganizer
from osa_tool.osatreesitter.docgen import DocGen
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter
from osa_tool.scheduler.scheduler import ModeScheduler
from osa_tool.scheduler.workflow_manager import (
    GitHubWorkflowManager,
    GitLabWorkflowManager,
    GitverseWorkflowManager,
    WorkflowManager,
)
from osa_tool.translation.dir_translator import DirectoryTranslator
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

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

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

        if create_fork:
            git_agent.create_and_checkout_branch()

        # Repository Analysis Report generation
        # NOTE: Must run first - switches GitHub branches
        if plan.get("report"):
            rich_section("Report generation")
            plan.mark_started("report")
            analytics = ReportGenerator(config_loader, git_agent.metadata)
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
            content = loop.run_until_complete(DocValidator(config_loader).validate(plan.get("attachment")))
            if content:
                va_re_gen = ValidationReportGenerator(config_loader, git_agent.metadata)
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
            content = loop.run_until_complete(PaperValidator(config_loader).validate(plan.get("attachment")))
            if content:
                va_re_gen = ValidationReportGenerator(config_loader, git_agent.metadata)
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
            plan.mark_started("translate_dirs")
            translation = DirectoryTranslator(config_loader)
            if translation.rename_directories_and_files():
                plan.mark_done("translate_dirs")
            else:
                plan.mark_failed("translate_dirs")

        # Docstring generation
        if plan.get("docstring"):
            rich_section("Docstrings generation")
            plan.mark_started("docstring")
            if generate_docstrings(config_loader, loop, args.ignore_list):
                plan.mark_done("docstring")
            else:
                plan.mark_failed("docstring")

        # License compiling
        if license_type := plan.get("ensure_license"):
            rich_section("License generation")
            LicenseCompiler(config_loader, git_agent.metadata, license_type).run() # TODO: Добавить план
            # what_has_been_done.mark_did("ensure_license")

        # Generate community documentation
        if plan.get("community_docs"):
            rich_section("Community docs generation")
            plan.mark_started("community_docs")
            if generate_documentation(config_loader, git_agent.metadata):
                plan.mark_done("community_docs")
            else:
                plan.mark_failed("community_docs")

        # Requirements generation
        if plan.get("requirements"):
            rich_section("Requirements generation")
            plan.mark_started("requirements")
            if generate_requirements(args.repository):
                plan.mark_done("requirements")
            else:
                plan.mark_failed("requirements")

        # Readme generation
        if plan.get("readme"):
            rich_section("README generation")
            plan.mark_started("readme")
            readme_agent = ReadmeAgent(
                config_loader, git_agent.metadata, plan
            ) # TODO: Посмотреть кодом
            try:
                readme_agent.generate_readme()
                plan.mark_done("readme")
            except ValueError:
                plan.mark_failed("readme")

        # Readme translation
        translate_readme = plan.get("translate_readme")
        if translate_readme:
            rich_section("README translation")
            plan.mark_started("translate_readme") # TODO: А я вроде поменял
            if ReadmeTranslator(config_loader, git_agent.metadata, translate_readme).translate_readme():
                plan.mark_done("translate_readme")
            else:
                plan.mark_failed("translate_readme")

        # About section generation
        about_gen = None
        if plan.get("about"):
            rich_section("About Section generation")
            about_gen = AboutGenerator(config_loader, git_agent)
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
            workflow_manager.update_workflow_config(config_loader, plan)
            if workflow_manager.generate_workflow(config_loader):
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
            WhatHasBeenDoneReportGenerator(
                config_loader, plan.list_for_report, git_agent.metadata
            ).build_pdf() # TODO: Глянуть

        elapsed_time = time.time() - start_time
        rich_section(f"All operations completed successfully in total time: {format_time(elapsed_time)}")
        sys.exit(0)

    except Exception as e:
        logger.error("Error: %s", e, exc_info=False if args.web_mode else True)
        sys.exit(1)

    finally:
        loop.close()


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


def generate_requirements(repo_url) -> bool:
    """
    Returns:
        Has the task been completed successfully
    """
    logger.info(f"Starting the generation of requirements")
    repo_path = Path(parse_folder_name(repo_url)).resolve()
    try:
        result = subprocess.run(
            ["pipreqs", "--scan-notebooks", "--force", "--encoding", "utf-8", repo_path],
            capture_output=True,
            text=True,
            check=True,
        )
        logger.info(f"Requirements generated successfully at: {repo_path}")
        logger.debug(result)
    except subprocess.CalledProcessError as e:
        logger.error(f"Error while generating project's requirements: {e.stderr}")
        return False
    return True


def generate_docstrings(config_loader: ConfigLoader, loop: asyncio.AbstractEventLoop, ignore_list: list[str]) -> bool:
    """Generates a docstrings for .py's classes and methods of the provided repository.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.
        loop: Link to the event loop in the main thread.
    Returns:
        Has the task been completed successfully
    """

    sem = asyncio.Semaphore(100)
    workers = multiprocessing.cpu_count()
    repo_url = config_loader.config.git.repository
    repo_path = parse_folder_name(repo_url)

    try:
        rate_limit = config_loader.config.llm.rate_limit
        ts = OSA_TreeSitter(repo_path, ignore_list)
        res = ts.analyze_directory(ts.cwd)
        dg = DocGen(config_loader)

        # getting the project source code and start generating docstrings
        source_code = loop.run_until_complete(dg._get_project_source_code(res, sem))

        # first stage
        # generate for functions and methods first
        fn_generated_docstrings = loop.run_until_complete(
            dg._generate_docstrings_for_items(res, docstring_type=("functions", "methods"), rate_limit=rate_limit)
        )
        fn_augmented = dg._run_in_executor(
            res, source_code, generated_docstrings=fn_generated_docstrings, n_workers=workers
        )
        loop.run_until_complete(dg._write_augmented_code(res, augmented_code=fn_augmented, sem=sem))

        # re-analyze project after docstrings writing
        res = ts.analyze_directory(ts.cwd)
        source_code = loop.run_until_complete(dg._get_project_source_code(ts.analyze_directory(ts.cwd), sem))

        # then generate description for classes based on filled methods docstrings
        cl_generated_docstrings = loop.run_until_complete(
            dg._generate_docstrings_for_items(res, docstring_type="classes", rate_limit=rate_limit)
        )
        cl_augmented = dg._run_in_executor(
            res, source_code, generated_docstrings=cl_generated_docstrings, n_workers=workers
        )
        loop.run_until_complete(dg._write_augmented_code(res, augmented_code=cl_augmented, sem=sem))

        # generate the main idea
        loop.run_until_complete(dg.generate_the_main_idea(res))

        # re-analyze project and read augmented source code
        res = ts.analyze_directory(ts.cwd)
        source_code = loop.run_until_complete(dg._get_project_source_code(res, sem))

        # update docstrings for project based on generated main idea
        generated_after_idea = loop.run_until_complete(
            dg._generate_docstrings_for_items(
                res, docstring_type=("functions", "methods", "classes"), rate_limit=rate_limit
            )
        )

        # augment the source code and persist it
        augmented_after_idea = dg._run_in_executor(res, source_code, generated_after_idea, workers)
        loop.run_until_complete(dg._write_augmented_code(res, augmented_after_idea, sem))

        modules_summaries = loop.run_until_complete(dg.summarize_submodules(res, rate_limit))
        dg.generate_documentation_mkdocs(repo_path, res, modules_summaries)
        dg.create_mkdocs_git_workflow(repo_url, repo_path)

    except Exception as e:
        dg._purge_temp_files(repo_path)
        logger.error("Error while generating codebase documentation: %s", repr(e), exc_info=True)
        return False
    return True

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
