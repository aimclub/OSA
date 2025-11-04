import os

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.logger import logger
from osa_tool.readmegen.generator.builder import MarkdownBuilder
from osa_tool.readmegen.generator.builder_article import MarkdownBuilderArticle
from osa_tool.readmegen.models.llm_service import LLMClient
from osa_tool.readmegen.utils import remove_extra_blank_lines, save_sections
from osa_tool.utils import parse_folder_name


def readme_agent(
    config_loader: ConfigLoader, article: str | None, refine_readme: bool, metadata: RepositoryMetadata
) -> None:
    """Generates a README.md file for the specified GitHub repository.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.
        article: Optional link to the pdf file of the article.
        refine_readme: Optional flag for refinement README.
        metadata: Git repository metadata.

    Raises:
        Exception: If an error occurs during README.md generation.
    """
    repo_url = config_loader.config.git.repository
    repo_path = os.path.join(os.getcwd(), parse_folder_name(repo_url))
    file_to_save = os.path.join(repo_path, "README.md")
    llm_client = LLMClient(config_loader, metadata)

    logger.info("Started generating README.md. Processing the repository: %s", repo_url)
    try:
        if article is None:
            responses = llm_client.get_responses()
            (core_features, overview, getting_started) = responses

            builder = MarkdownBuilder(config_loader, metadata, overview, core_features, getting_started)
        else:
            responses = llm_client.get_responses_article(article)
            (overview, content, algorithms, getting_started) = responses

            builder = MarkdownBuilderArticle(config_loader, metadata, overview, content, algorithms, getting_started)

        readme_content = builder.build()

        if refine_readme:
            readme_content = llm_client.refine_readme(readme_content)

        readme_content = llm_client.clean(readme_content)

        save_sections(readme_content, file_to_save)
        remove_extra_blank_lines(file_to_save)
        logger.info(f"README.md successfully generated in folder {repo_path}")
    except Exception as e:
        logger.error("Error while generating: %s", repr(e), exc_info=True)
        raise ValueError("Failed to generate README.md.")
