import os

from osa_tool.readmegen.generator.builder import MarkdownBuilder
from osa_tool.readmegen.models.llm_service import LLMClient
from osa_tool.readmegen.utils import save_sections
from osa_tool.utils import logger, parse_folder_name


def readme_agent(config_loader, article: str | None) -> None:
    """Generates a README.md file for the specified GitHub repository.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.
        article: Optional link to the pdf file of the article.

    Raises:
        Exception: If an error occurs during README.md generation.
    """
    repo_url = config_loader.config.git.repository
    repo_path = os.path.join(os.getcwd(), parse_folder_name(repo_url))
    file_to_save = os.path.join(repo_path, "README.md")

    logger.info("Started generating README.md. Processing the repository: %s", repo_url)
    try:
        if article is None:
            responses = LLMClient(config_loader).get_responses()

            (
                core_features,
                overview
            ) = responses

            readme_content = MarkdownBuilder(config_loader, overview, core_features).build()
            save_sections(readme_content, file_to_save)

    except Exception as e:
        logger.error("Error while generating: %s", repr(e), exc_info=True)
        raise ValueError("Failed to generate README.md.")
