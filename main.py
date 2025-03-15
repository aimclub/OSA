import logging
import os

from typing import Optional

from rich.logging import RichHandler

from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.arguments_parser import get_cli_args
from osa_tool.github_agent.github_agent import GithubAgent
from osa_tool.osatreesitter.docgen import DocGen
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter
from osa_tool.readmeai.config.settings import ConfigLoader, GitSettings
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.readmeai.readme_core import readme_agent
from osa_tool.translation.dir_translator import DirectoryTranslator
from osa_tool.utils import (
    osa_project_root,
    parse_folder_name
)

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)

logger = logging.getLogger("rich")


def main():
    """Main function to generate a README.md file for a GitHub repository.

    Handles command-line arguments, clones the repository, creates and checks out a branch,
    generates the README.md file, and commits and pushes the changes.
    """

    # Create a command line argument parser
    args = get_cli_args()
    repo_url = args.repository
    api = args.api
    base_url = args.base_url
    model_name = args.model
    article = args.article

    try:
        # Load configurations and update
        config = load_configuration(repo_url, api, base_url, model_name, article)

        # Initialize GitHub agent and perform operations
        github_agent = GithubAgent(repo_url)
        github_agent.star_repository()
        github_agent.create_fork()
        github_agent.clone_repository()
        github_agent.create_and_checkout_branch()

        analytics = ReportGenerator(config)
        analytics.build_pdf()

        # Auto translating names of directories
        if args.translate_dirs:
            translation = DirectoryTranslator(config)
            translation.rename_directories()
        '''
        # Docstring generation
        generate_docstrings(config)

        # Readme generation
        readme_agent(config, article)
        
        github_agent.commit_and_push_changes()
        github_agent.create_pull_request()
        '''
        logger.info("All operations completed successfully.")
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)


def generate_docstrings(config_loader) -> None:
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
        logger.error("Error while docstring generation: %s", repr(e),
                     exc_info=True)


def load_configuration(
        repo_url: str,
        api: str,
        base_url: str,
        model_name: str,
        article: Optional[str]
) -> ConfigLoader:
    """
    Loads configuration for osa_tool.

    Args:
        repo_url: URL of the GitHub repository.
        api: LLM API service provider.
        base_url: URL of the provider compatible with API OpenAI
        model_name: Specific LLM model to use.
        article: Link to the pdf file of the article. Can be None.

    Returns:
        config_loader: The configuration object which contains settings for osa_tool.
    """
    if article is None:

        config_loader = ConfigLoader(
            config_dir=os.path.join(osa_project_root(), "osa_tool", "config",
                                    "standart"))
    else:
        config_loader = ArticleConfigLoader(
            config_dir=os.path.join(osa_project_root(), "osa_tool", "config",
                                    "with_article"))

    config_loader.config.git = GitSettings(repository=repo_url)
    config_loader.config.llm = config_loader.config.llm.model_copy(
        update={
            "api": api,
            "url": base_url,
            "model": model_name
        }
    )
    logger.info("Config successfully updated and loaded")
    return config_loader


if __name__ == "__main__":
    main()
