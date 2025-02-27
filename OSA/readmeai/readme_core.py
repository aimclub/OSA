import logging
import os
from typing import Optional

from rich.logging import RichHandler

from OSA.readmeai.generators.builder import MarkdownBuilder
from OSA.readmeai.ingestion.models import RepositoryContext
from OSA.readmeai.ingestion.pipeline import RepositoryProcessor
from OSA.readmeai.models.base import BaseModelHandler
from OSA.readmeai.postprocessor import response_cleaner
from OSA.readmeai.readmegen_article.generators.builder import ArticleMarkdownBuilder
from OSA.readmeai.utils.file_handler import FileHandler
from OSA.utils import parse_folder_name

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)

logger = logging.getLogger("rich")


def readme_agent(config_loader, article: Optional[str]) -> None:
    """Generates a README.md file for the specified GitHub repository.

    Args:
        config_loader: The configuration object which contains settings for OSA.
        article: Optional link to the pdf file of the article.

    Raises:
        Exception: If an error occurs during README.md generation.
    """
    repo_url = config_loader.config.git.repository
    repo_path = os.path.join(os.getcwd(), parse_folder_name(repo_url))
    file_to_save = os.path.join(repo_path, "README.md")

    logger.info("Started generating README.md. Processing the repository: %s"
                , repo_url)

    try:
        processor: RepositoryProcessor = RepositoryProcessor(
            config=config_loader
        )
        context: RepositoryContext = processor.process_repository(
            repo_path=repo_path
        )
        logger.info(f"Total files analyzed: {len(context.files)}")
        logger.info(f"Metadata extracted: {context.metadata}")
        logger.info(f"Dependencies: {context.dependencies}")
        logger.info(f"Languages: {context.language_counts}")

        if article is None:
            handler = BaseModelHandler(config_loader, context)
            responses = handler.batch_request()

            (
                file_summaries,
                core_features,
                overview,
            ) = responses

            config_loader.config.md.overview = config_loader.config.md.overview.format(
                response_cleaner.process_markdown(overview)
            )
            config_loader.config.md.core_features = config_loader.config.md.core_features.format(
                response_cleaner.process_markdown(core_features)
            )

        else:
            handler = BaseModelHandler(config_loader, context)
            responses = handler.article_batch_request()

            (
                file_summary,
                pdf_summary,
                overview,
                content,
                algorithms,
            ) = responses

            config_loader.config.md.overview = config_loader.config.md.overview.format(
                response_cleaner.process_markdown(overview)
            )
            config_loader.config.md.content = config_loader.config.md.content.format(
                response_cleaner.process_markdown(content)
            )
            config_loader.config.md.algorithms = config_loader.config.md.algorithms.format(
                response_cleaner.process_markdown(algorithms)
            )

        if article is None:
            readme_md_content = MarkdownBuilder(config_loader, context,
                                                repo_path).build()
        else:
            readme_md_content = ArticleMarkdownBuilder(config_loader).build()

        FileHandler().write(file_to_save, readme_md_content)
        logger.info("README.md successfully generated in folder: %s",
                    repo_path)
    except Exception as e:
        logger.error("Error while generating: %s", repr(e), exc_info=True)
        raise ValueError("Failed to generate README.md.")