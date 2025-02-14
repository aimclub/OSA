import os
import argparse
import logging
from rich.logging import RichHandler
from typing import Optional
from readmegen_article.config.settings import ArticleConfigLoader
from readmeai.config.settings import ConfigLoader, GitSettings
from readmeai.main import readme_generator
from OSA.github_agent.github_agent import GithubAgent
from OSA.utils import parse_folder_name
from OSA.osatreesitter.osa_treesitter import OSA_TreeSitter
from OSA.osatreesitter.docgen import DocGen

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)

logger = logging.getLogger("rich")


def main():
    """Main function to generate a README.md file for a GitHub repository.

    Handles command-line arguments, clones the repository, creates and checks out a branch,
    generates the README.md file, and commits and pushes the changes.
    """
    # Create a command line argument parser
    parser = argparse.ArgumentParser(
        description="Generate README.md for a GitHub repository"
    )
    parser.add_argument(
        "repo_url",
        type=str,
        help="URL of the GitHub repository"
    )

    parser.add_argument(
        "api",
        type=str,
        help="LLM API service provider",
        nargs="?",
        default="llama"
    )

    parser.add_argument(
        "model_name",
        type=str,
        help="Specific LLM model to use",
        nargs="?",
        default="llama"
    )

    parser.add_argument(
        "--article",
        type=str,
        help=(
            "Select a README template for a repository with an article. "
            "You can also provide a link to the pdf file of the article "
            "after the --article option."
        ),
        nargs="?",
        const="",
        default=None
    )

    args = parser.parse_args()
    repo_url = args.repo_url
    api = args.api
    model_name = args.model_name
    article = args.article

    try:
        
        # Initialize GitHub agent and perform operations
        github_agent = GithubAgent(repo_url)
        github_agent.star_repository()
        github_agent.clone_repository()
        github_agent.create_and_checkout_branch()
        
        # Docstring generation
        ts = OSA_TreeSitter(os.path.basename(repo_url))
        res = ts.analyze_directory(ts.cwd)
        dg = DocGen()
        dg.process_python_file(res)
        
        # Readme generation
        readme_agent(repo_url, api, model_name, article)
        
        github_agent.commit_and_push_changes()
        github_agent.create_pull_request()
        logger.info("All operations completed successfully.")
        
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)


def readme_agent(repo_url: str, api: str, model_name: str, article: Optional[str]) -> None:
    """Generates a README.md file for the specified GitHub repository.

    Args:
        api: LLM API service provider
        model_name: Specific LLM model to use
        repo_url: URL of the GitHub repository
        article: Optional link to the pdf file of the article.

    Raises:
        Exception: If an error occurs during README.md generation.
    """
    
    logger.info("Started generating README.md. Processing the repository: %s", repo_url)

    try:
        # Load configurations and update config
        if article is None:
            config_loader = ConfigLoader(config_dir="OSA/config/standart")
        else:
            config_loader = ArticleConfigLoader(config_dir="OSA/config/with_article")
        config_loader.config.git = GitSettings(repository=repo_url)
        config_loader.config.llm = config_loader.config.llm.model_copy(
            update={
                "api": api,
                "model": model_name
            }
        )

        # Define output directory and ensure it exists
        output_dir = os.path.join(os.getcwd(), parse_folder_name(repo_url))
        os.makedirs(output_dir, exist_ok=True)
        file_to_save = os.path.join(output_dir, "README.md")

        # Generate README.md
        readme_generator(config_loader, file_to_save, article)

        logger.info("README.md successfully generated in folder: %s", output_dir)

    except Exception as e:
        logger.error("Error while generating: %s", repr(e), exc_info=True)


if __name__ == "__main__":
    main()
