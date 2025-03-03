import argparse
import logging
import os
from typing import Optional

from rich.logging import RichHandler

from osa_tool.github_agent.github_agent import GithubAgent
from osa_tool.osatreesitter.docgen import DocGen
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter
from osa_tool.readmeai.config.settings import ConfigLoader, GitSettings
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.readmeai.readme_core import readme_agent
from osa_tool.translation.dir_translator import DirectoryTranslator
from osa_tool.utils import osa_project_root

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
    parser = argparse.ArgumentParser(
        description="Generate README.md for a GitHub repository",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument(
        "-r",
        "--repository",
        type=str,
        help="URL of the GitHub repository",
        required=True
    )
    parser.add_argument(
        "--api",
        type=str,
        help="LLM API service provider",
        nargs="?",
        choices=["llama", "openai", "vsegpt"],
        default="llama",
    )
    parser.add_argument(
        "--model",
        type=str,
        help=(
            "Specific LLM model to use. "
            "To see available models go there:\n"
            "1. https://vsegpt.ru/Docs/Models\n"
            "2. https://platform.openai.com/docs/models"
        ),
        nargs="?",
        default="llama",
    )
    parser.add_argument(
        "--article",
        type=str,
        help=(
            "Select a README template for a repository with an article.\n"
            "You can also provide a link to the pdf file of the article\n"
            "after the --article option."
        ),
        nargs="?",
        const="",
        default=None,
    )
    parser.add_argument(
        "--translate-dirs",
        action="store_true",
        help=(
            "Enable automatic translation of the directory name into English."
        ),
    )

    args = parser.parse_args()
    repo_url = args.repository
    api = args.api
    model_name = args.model
    article = args.article

    try:
        # Load configurations and update
        config = load_configuration(repo_url, api, model_name, article)

        # Initialize GitHub agent and perform operations
        github_agent = GithubAgent(repo_url)
        github_agent.star_repository()
        github_agent.create_fork()
        github_agent.clone_repository()
        github_agent.create_and_checkout_branch()

        # Auto translating names of directories
        if args.translate_dirs:
            translation = DirectoryTranslator(config)
            translation.rename_directories()

        # Docstring generation
        generate_docstrings(config)

        # Readme generation
        readme_agent(config, article)

        github_agent.commit_and_push_changes()
        github_agent.create_pull_request()
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
        ts = OSA_TreeSitter(os.path.basename(repo_url))
        res = ts.analyze_directory(ts.cwd)
        dg = DocGen(config_loader)
        dg.process_python_file(res)

    except Exception as e:
        logger.error("Error while docstring generation: %s", repr(e),
                     exc_info=True)
        raise ValueError("Failed to generate docstrings.")


def load_configuration(
        repo_url: str,
        api: str,
        model_name: str,
        article: Optional[str]
) -> ConfigLoader:
    """
    Loads configuration for osa_tool.

    Args:
        repo_url (str): URL of the GitHub repository.
        api (str): LLM API service provider.
        model_name (str): Specific LLM model to use.
        article (Optional[str]): Link to the pdf file of the article. Can be None.

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
            "model": model_name
        }
    )
    logger.info("Config successfully updated and loaded")
    return config_loader


if __name__ == "__main__":
    main()
