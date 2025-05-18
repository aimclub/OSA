import os
from typing import List

from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.arguments_parser import get_cli_args
from osa_tool.config.settings import ConfigLoader, GitSettings
from osa_tool.convertion.notebook_converter import NotebookConverter
from osa_tool.docs_generator.docs_run import generate_documentation
from osa_tool.docs_generator.license import compile_license_file
from osa_tool.github_agent.github_agent import GithubAgent
from osa_tool.github_workflow.workflow_manager import generate_github_workflows
from osa_tool.organization.repo_organizer import RepoOrganizer
from osa_tool.osatreesitter.docgen import DocGen
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter
from osa_tool.readmegen.readme_core import readme_agent
from osa_tool.scheduler import ModeScheduler
from osa_tool.translation.dir_translator import DirectoryTranslator
from osa_tool.utils import (
    delete_repository,
    logger,
    parse_folder_name
)


def main():
    """Main function to generate a README.md file for a GitHub repository.

    Handles command-line arguments, clones the repository, creates and checks out a branch,
    generates the README.md file, and commits and pushes the changes.
    """

    # Create a command line argument parser
    args = get_cli_args()
    publish_results = not args.not_publish_results

    # Extract workflow-related arguments
    generate_workflows = args.generate_workflows

    try:
        # Load configurations and update
        config = load_configuration(
            repo_url=args.repository,
            api=args.api,
            base_url=args.base_url,
            model_name=args.model,
        )

        # Initialize ModeScheduler
        scheduler = ModeScheduler(args)
        plan = scheduler.plan

        # Initialize GitHub agent and perform operations
        github_agent = GithubAgent(args.repository, args.branch)
        if publish_results:
            github_agent.star_repository()
            github_agent.create_fork()
        github_agent.clone_repository()
        if publish_results:
            github_agent.create_and_checkout_branch()

        # .ipynb to .py convertion
        if plan.get("convert_notebooks"):
            convert_notebooks(args.repository, args.convert_notebooks)

        # Repository Analysis Report generation
        sourcerank = SourceRank(config)
        if plan.get("generate_report"):
            analytics = ReportGenerator(config, sourcerank, github_agent.clone_dir)
            analytics.build_pdf()
            if publish_results:
                github_agent.upload_report(analytics.filename)

        # Auto translating names of directories
        if plan.get("translate_dirs"):
            translation = DirectoryTranslator(config)
            translation.rename_directories_and_files()

        # Docstring generation
        if plan.get("generate_docstring"):
            generate_docstrings(config)

        # License compiling
        if plan.get("ensure_license"):
            compile_license_file(sourcerank, args.ensure_license)

        # Generate community documentation
        if plan.get("community_docs"):
            generate_documentation(config)

        # Readme generation
        if plan.get("generate_readme"):
            readme_agent(config, args.article)

        # Generate GitHub workflows
        if generate_workflows:
            generate_github_workflows(config)

        # Organize repository by adding 'tests' and 'examples' directories if they aren't exist
        if plan.get("organize"):
            organizer = RepoOrganizer(os.path.join(os.getcwd(), parse_folder_name(args.repository)))
            organizer.organize()

        if publish_results:
            github_agent.commit_and_push_changes()
            github_agent.create_pull_request()

        if args.delete_dir:
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
        model_name: str
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
