import os
import asyncio
import subprocess
from typing import Optional

from pathlib import Path

from osa_tool.aboutgen.about_generator import AboutGenerator
from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.arguments_parser import (
    build_parser_from_yaml,
    get_keys_from_group_in_yaml,
)
from osa_tool.config.settings import ConfigLoader, GitSettings
from osa_tool.convertion.notebook_converter import NotebookConverter
from osa_tool.docs_generator.docs_run import generate_documentation
from osa_tool.docs_generator.license import compile_license_file
from osa_tool.git_agent.git_agent import GitAgent
from osa_tool.organization.repo_organizer import RepoOrganizer
from osa_tool.osatreesitter.docgen import DocGen
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter
from osa_tool.readmegen.readme_core import readme_agent
from osa_tool.scheduler.scheduler import ModeScheduler
from osa_tool.scheduler.workflow_manager import (
    generate_github_workflows,
    update_workflow_config,
)
from osa_tool.translation.dir_translator import DirectoryTranslator
from osa_tool.utils import (
    build_arguments_path,
    delete_repository,
    logger,
    parse_folder_name,
    rich_section,
)


def main():
    """Main function to generate a README.md file for a Git repository.

    Handles command-line arguments, clones the repository, creates and checks out a branch,
    generates the README.md file, and commits and pushes the changes.
    """

    # Create a command line argument parser
    parser = build_parser_from_yaml(build_arguments_path())
    args = parser.parse_args()
    workflow_keys = get_keys_from_group_in_yaml(build_arguments_path(), "workflow")
    create_fork = not args.no_fork
    create_pull_request = not args.no_pull_request

    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)

    try:
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

        # Initialize Git agent and perform operations
        git_agent = GitAgent(args.repository, args.branch)
        if create_fork:
            git_agent.star_repository()
            git_agent.create_fork()
        git_agent.clone_repository()

        # Initialize ModeScheduler
        sourcerank = SourceRank(config)
        scheduler = ModeScheduler(config, sourcerank, args, workflow_keys)
        plan = scheduler.plan

        if create_fork:
            git_agent.create_and_checkout_branch()

        # .ipynb to .py convertion
        if plan.get("convert_notebooks"):
            rich_section("Jupyter notebooks convertion")
            convert_notebooks(args.repository, plan.get("convert_notebooks"))

        # Repository Analysis Report generation
        if plan.get("report"):
            rich_section("Report generation")
            analytics = ReportGenerator(config, sourcerank)
            analytics.build_pdf()
            if create_fork:
                git_agent.upload_report(analytics.filename, analytics.output_path)

        # Auto translating names of directories
        if plan.get("translate_dirs"):
            rich_section("Directory and file translation")
            translation = DirectoryTranslator(config)
            translation.rename_directories_and_files()

        # Docstring generation
        if plan.get("docstring"):
            rich_section("Docstrings generation")
            loop.run_until_complete(generate_docstrings(config))

        # License compiling
        if plan.get("ensure_license"):
            rich_section("License generation")
            compile_license_file(sourcerank, plan.get("ensure_license"))

        # Generate community documentation
        if plan.get("community_docs"):
            rich_section("Community docs generation")
            generate_documentation(config)

        # Requirements generation
        if plan.get("requirements"):
            rich_section("Requirements generation")
            generate_requirements(args.repository)

        # Readme generation
        if plan.get("readme"):
            rich_section("README generation")
            readme_agent(config, plan.get("article"), plan.get("refine_readme"))

        # About section generation
        about_gen = None
        if plan.get("about"):
            rich_section("About Section generation")
            about_gen = AboutGenerator(config)
            about_gen.generate_about_content()
            if create_fork:
                git_agent.update_about_section(about_gen.get_about_content())
            if not create_pull_request:
                logger.info("About section:\n" + about_gen.get_about_section_message())

        # Generate GitHub workflows
        if plan.get("generate_workflows"):
            rich_section("Workflows generation")
            update_workflow_config(config, plan, workflow_keys)
            generate_github_workflows(config)

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
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)
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


async def generate_docstrings(config_loader: ConfigLoader) -> None:
    """Generates a docstrings for .py's classes and methods of the provided repository.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.

    """
    try:
        repo_url = config_loader.config.git.repository
        rate_limit = config_loader.config.llm.rate_limit
        repo_path = parse_folder_name(repo_url)
        ts = OSA_TreeSitter(repo_path)
        res = ts.analyze_directory(ts.cwd)
        dg = DocGen(config_loader)
        await dg.process_python_file(res, rate_limit)
        await dg.generate_the_main_idea(res)
        await dg.process_python_file(res, rate_limit)
        modules_summaries = await dg.summarize_submodules(res, rate_limit)
        dg.generate_documentation_mkdocs(repo_path, res, modules_summaries)
        dg.create_mkdocs_github_workflow(repo_url, repo_path)

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

    config_loader.config.git = GitSettings(repository=repo_url)
    config_loader.config.llm = config_loader.config.llm.model_copy(
        update={
            "api": api,
            "url": base_url,
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
