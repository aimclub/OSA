import asyncio
import multiprocessing
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from pydantic import ValidationError

from osa_tool.aboutgen.about_generator import AboutGenerator
from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.arguments_parser import build_parser_from_yaml
from osa_tool.config.settings import ConfigLoader, GitSettings
from osa_tool.conversion.notebook_converter import NotebookConverter
from osa_tool.docs_generator.docs_run import generate_documentation
from osa_tool.docs_generator.license import compile_license_file
from osa_tool.git_agent.git_agent import GitHubAgent, GitLabAgent, GitverseAgent
from osa_tool.logger import setup_logging, logger
from osa_tool.organization.repo_organizer import RepoOrganizer
from osa_tool.osatreesitter.docgen import DocGen
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter
from osa_tool.readmegen.readme_core import readme_agent
from osa_tool.scheduler.scheduler import ModeScheduler
from osa_tool.scheduler.workflow_manager import (
    GitHubWorkflowManager,
    GitLabWorkflowManager,
    GitverseWorkflowManager,
)
from osa_tool.translation.dir_translator import DirectoryTranslator
from osa_tool.translation.readme_translator import ReadmeTranslator
from osa_tool.utils import delete_repository, parse_folder_name, rich_section, osa_project_root
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
    parser = build_parser_from_yaml()
    args = parser.parse_args()
    create_fork = not args.no_fork
    create_pull_request = not args.no_pull_request

    # Initialize logging
    logs_dir = os.path.join(os.path.dirname(osa_project_root()), "logs")
    repo_name = parse_folder_name(args.repository)
    setup_logging(repo_name, logs_dir)

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    try:
        # Switch to output directory if present
        if args.output:
            output_path = Path(args.output).resolve()
            if not output_path.exists():
                output_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory: {output_path}")
            os.chdir(output_path)
            logger.info(f"Output path changed to {output_path}")

        # Load configurations and update
        config = load_configuration(
            repo_url=args.repository,
            api=args.api,
            base_url=args.base_url,
            model_name=args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            top_p=args.top_p,
        )

        # Initialize Git agent and Workflow Manager for used platform, perform operations
        if "github.com" in args.repository:
            git_agent = GitHubAgent(args.repository, args.branch)
            workflow_manager = GitHubWorkflowManager(args.repository, git_agent.metadata, args)
        elif "gitlab.com" in args.repository:
            git_agent = GitLabAgent(args.repository, args.branch)
            workflow_manager = GitLabWorkflowManager(args.repository, git_agent.metadata, args)
        elif "gitverse.ru" in args.repository:
            git_agent = GitverseAgent(args.repository, args.branch)
            workflow_manager = GitverseWorkflowManager(args.repository, git_agent.metadata, args)
        else:
            raise ValueError(f"Cannot initialize Git Agent and Workflow Manager for this platform: {args.repository}")

        if create_fork:
            git_agent.star_repository()
            git_agent.create_fork()
        git_agent.clone_repository()

        # Initialize ModeScheduler
        sourcerank = SourceRank(config)
        scheduler = ModeScheduler(config, sourcerank, args, workflow_manager, git_agent.metadata)
        plan = scheduler.plan

        if create_fork:
            git_agent.create_and_checkout_branch()

        # Repository Analysis Report generation
        # NOTE: Must run first - switches GitHub branches
        if plan.get("report"):
            rich_section("Report generation")
            analytics = ReportGenerator(config, sourcerank, git_agent.metadata)
            analytics.build_pdf()
            if create_fork:
                git_agent.upload_report(analytics.filename, analytics.output_path)

        # NOTE: Must run first - switches GitHub branches
        if path_to_doc := plan.get("validate_doc"):
            rich_section("Document validation")
            content = DocValidator(config).validate(path_to_doc)
            va_re_gen = ValidationReportGenerator(config, git_agent.metadata, sourcerank)
            va_re_gen.build_pdf("Document", content)
            if create_fork:
                git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)

        # NOTE: Must run first - switches GitHub branches
        if plan.get("validate_paper"):
            rich_section("Paper validation")
            content = PaperValidator(config).validate(plan.get("article"))
            va_re_gen = ValidationReportGenerator(config, git_agent.metadata, sourcerank)
            va_re_gen.build_pdf("Paper", content)
            if create_fork:
                git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)

        # .ipynb to .py conversion
        if notebook := plan.get("convert_notebooks"):
            rich_section("Jupyter notebooks conversion")
            convert_notebooks(args.repository, notebook)

        # Auto translating names of directories
        if plan.get("translate_dirs"):
            rich_section("Directory and file translation")
            translation = DirectoryTranslator(config)
            translation.rename_directories_and_files()

        # Docstring generation
        if plan.get("docstring"):
            rich_section("Docstrings generation")
            generate_docstrings(config, loop)

        # License compiling
        if license_type := plan.get("ensure_license"):
            rich_section("License generation")
            compile_license_file(sourcerank, license_type, git_agent.metadata)

        # Generate community documentation
        if plan.get("community_docs"):
            rich_section("Community docs generation")
            generate_documentation(config, git_agent.metadata)

        # Requirements generation
        if plan.get("requirements"):
            rich_section("Requirements generation")
            generate_requirements(args.repository)

        # Readme generation
        if plan.get("readme"):
            rich_section("README generation")
            readme_agent(config, plan.get("article"), plan.get("refine_readme"), git_agent.metadata)

        # Readme translation
        translate_readme = plan.get("translate_readme")
        if translate_readme:
            rich_section("README translation")
            ReadmeTranslator(config, git_agent.metadata, translate_readme).translate_readme()

        # About section generation
        about_gen = None
        if plan.get("about"):
            rich_section("About Section generation")
            about_gen = AboutGenerator(config, git_agent)
            about_gen.generate_about_content()
            if create_fork:
                git_agent.update_about_section(about_gen.get_about_content())
            if not create_pull_request:
                logger.info("About section:\n" + about_gen.get_about_section_message())

        # Generate platform-specified CI/CD files
        if plan.get("generate_workflows"):
            rich_section("Workflows generation")
            workflow_manager.update_workflow_config(config, plan)
            workflow_manager.generate_workflow(config)

        # Organize repository by adding 'tests' and 'examples' directories if they aren't exist
        if plan.get("organize"):
            rich_section("Repository organization")
            organizer = RepoOrganizer(os.path.join(os.getcwd(), parse_folder_name(args.repository)))
            organizer.organize()

        if create_fork and create_pull_request:
            rich_section("Publishing changes")
            if git_agent.commit_and_push_changes(force=True):
                git_agent.create_pull_request(body=about_gen.get_about_section_message() if about_gen else "")
            else:
                logger.warning("No changes were committed — pull request will not be created.")
                if about_gen:
                    logger.info("About section:\n" + about_gen.get_about_section_message())

        if plan.get("delete_dir"):
            rich_section("Repository deletion")
            delete_repository(args.repository)

        rich_section("All operations completed successfully")
        sys.exit(0)

    except Exception as e:
        logger.error("Error: %s", e, exc_info=False if args.web_mode else True)
        sys.exit(1)

    finally:
        loop.close()


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


def generate_requirements(repo_url):
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


def generate_docstrings(config_loader: ConfigLoader, loop: asyncio.AbstractEventLoop) -> None:
    """Generates a docstrings for .py's classes and methods of the provided repository.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.
        loop: Link to the event loop in the main thread.
    """

    sem = asyncio.Semaphore(100)
    workers = multiprocessing.cpu_count()
    repo_url = config_loader.config.git.repository
    repo_path = parse_folder_name(repo_url)

    try:
        rate_limit = config_loader.config.llm.rate_limit
        ts = OSA_TreeSitter(repo_path)
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


def load_configuration(
    repo_url: str,
    api: str,
    base_url: str,
    model_name: str,
    temperature: Optional[str] = None,
    max_tokens: Optional[str] = None,
    top_p: Optional[str] = None,
) -> ConfigLoader:
    """
    Loads configuration for osa_tool.

    Args:
        repo_url: URL of the GitHub repository.
        api: LLM API service provider.
        base_url: URL of the provider compatible with API OpenAI
        model_name: Specific LLM model to use.
        temperature: Sampling temperature for the model.
        max_tokens: Maximum number of tokens to generate.
        top_p: Nucleus sampling value.

    Returns:
        config_loader: The configuration object which contains settings for osa_tool.
    """
    config_loader = ConfigLoader()

    try:
        config_loader.config.git = GitSettings(repository=repo_url)
    except ValidationError as es:
        first_error = es.errors()[0]
        raise ValueError(f"{first_error['msg']}{first_error['input']}")
    config_loader.config.llm = config_loader.config.llm.model_copy(
        update={
            "api": api,
            "base_url": base_url,
            "model": model_name,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
        }
    )
    logger.info("Config successfully updated and loaded")
    return config_loader


if __name__ == "__main__":
    main()
