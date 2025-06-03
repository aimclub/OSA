import os
from typing import List

from osa_tool.aboutgen.about_generator import AboutGenerator
from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.arguments_parser import get_cli_args, get_workflow_keys
from osa_tool.config.settings import ConfigLoader, GitSettings
from osa_tool.convertion.notebook_converter import NotebookConverter
from osa_tool.docs_generator.docs_run import generate_documentation
from osa_tool.docs_generator.license import compile_license_file
from osa_tool.github_agent.github_agent import GithubAgent
from osa_tool.organization.repo_organizer import RepoOrganizer
from osa_tool.osatreesitter.docgen import DocGen
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter
from osa_tool.readmegen.readme_core import readme_agent
from osa_tool.scheduler.scheduler import ModeScheduler
from osa_tool.scheduler.workflow_manager import generate_github_workflows, update_workflow_config
from osa_tool.translation.dir_translator import DirectoryTranslator
from osa_tool.utils import delete_repository, logger, parse_folder_name, rich_section


def main():
    """Main function to generate a README.md file for a GitHub repository.

    Handles command-line arguments, clones the repository, creates and checks out a branch,
    generates the README.md file, and commits and pushes the changes.
    """

    # Create a command line argument parser
    parser = get_cli_args()
    args = parser.parse_args()
    workflow_keys = get_workflow_keys(parser)
    publish_results = not args.not_publish_results

    try:
        # Load configurations and update
        config = load_configuration(
            repo_url=args.repository,
            api=args.api,
            base_url=args.base_url,
            model_name=args.model,
        )
        sourcerank = SourceRank(config)

        # Initialize GitHub agent and perform operations
        github_agent = GithubAgent(args.repository, args.branch)
        if publish_results:
            github_agent.star_repository()
            github_agent.create_fork()
        github_agent.clone_repository()

        # Initialize ModeScheduler
        scheduler = ModeScheduler(config, sourcerank, args, workflow_keys)
        plan = scheduler.plan

        if publish_results:
            github_agent.create_and_checkout_branch()

        # .ipynb to .py convertion
        if plan.get("convert_notebooks"):
            rich_section("Jupyter notebooks convertion")
            convert_notebooks(args.repository, plan.get("convert_notebooks"))

        # Repository Analysis Report generation
        if plan.get("report"):
            rich_section("Report generation")
            analytics = ReportGenerator(config, sourcerank, github_agent.clone_dir)
            analytics.build_pdf()
            if publish_results:
                github_agent.upload_report(analytics.filename)

        # Auto translating names of directories
        if plan.get("translate_dirs"):
            rich_section("Directory and file translation")
            translation = DirectoryTranslator(config)
            translation.rename_directories_and_files()

        # Docstring generation
        if plan.get("docstring"):
            rich_section("Docstrings generation")
            generate_docstrings(config)

        # License compiling
        if plan.get("ensure_license"):
            rich_section("License generation")
            compile_license_file(sourcerank, plan.get("ensure_license"))

        # Generate community documentation
        if plan.get("community_docs"):
            rich_section("Community docs generation")
            generate_documentation(config)

        # Readme generation
        if plan.get("readme"):
            rich_section("README generation")
            readme_agent(config, plan.get("article"))

        # About section generation
        about_gen = None
        if plan.get("about"):
            rich_section("About Section generation")
            about_gen = AboutGenerator(config)
            about_gen.generate_about_content()
            if publish_results:
                github_agent.update_about_section(about_gen.get_about_content())

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

        if publish_results:
            rich_section("Publishing changes")
            github_agent.commit_and_push_changes()
            github_agent.create_pull_request(body=about_gen.get_about_section_message())

        if plan.get("delete_dir"):
            rich_section("Repository deletion")
            delete_repository(args.repository)

        logger.info("All operations completed successfully.")
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)


def convert_notebooks(repo_url: str, notebook_paths: List[str] | None = None) -> None:
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


def generate_docstrings(config_loader: ConfigLoader) -> None:
    """Generates a docstrings for .py's classes and methods of the provided repository.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.

    """
    try:
        repo_url = config_loader.config.git.repository
        ts = OSA_TreeSitter(parse_folder_name(repo_url))
        res = ts.analyze_directory(ts.cwd)
        dg = DocGen(config_loader)
        dg.process_python_file(res)

    except Exception as e:
        logger.error("Error while docstring generation: %s", repr(e), exc_info=True)


def load_configuration(
    repo_url: str,
    api: str,
    base_url: str,
    model_name: str,
) -> ConfigLoader:
    """
    Loads configuration for osa_tool.

    Args:
        repo_url: URL of the GitHub repository.
        api: LLM API service provider.
        base_url: URL of the provider compatible with API OpenAI
        model_name: Specific LLM model to use.

    Returns:
        config_loader: The configuration object which contains settings for osa_tool.
    """
    config_loader = ConfigLoader()

    config_loader.config.git = GitSettings(repository=repo_url)
    config_loader.config.llm = config_loader.config.llm.model_copy(
        update={"api": api, "url": base_url, "model": model_name}
    )
    logger.info("Config successfully updated and loaded")
    return config_loader


if __name__ == "__main__":
    main()
