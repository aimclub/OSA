import tempfile

from readmegen.config.constants import ImageOptions
from readmegen.config.settings import ConfigLoader

from readmegen.generators.builder import MarkdownBuilder
from readmegen.ingestion.models import RepositoryContext
from readmegen.ingestion.pipeline import RepositoryProcessor
from readmegen.logger import get_logger
from readmegen.models.factory import ModelFactory
from readmegen.postprocessor import response_cleaner
from readmegen.readers.git.repository import load_data
from readmegen.utils.file_handler import FileHandler

_logger = get_logger(__name__)


def readme_generator(config: ConfigLoader, output_file: str) -> None:
    """Processes the repository and builds the README file."""

    with tempfile.TemporaryDirectory() as temp_dir:

        repo_path = load_data(config.config.git.repository, temp_dir)

        processor: RepositoryProcessor = RepositoryProcessor(config=config)
        context: RepositoryContext = processor.process_repository(
            repo_path=repo_path
        )

        log_repository_context(context)

        llm = ModelFactory.get_backend(config, context)
        responses = llm.batch_request()

        (
            file_summaries,
            core_features,
            overview,
        ) = responses

        config.config.md.overview = config.config.md.overview.format(
            response_cleaner.process_markdown(overview)
        )
        config.config.md.core_features = config.config.md.core_features.format(
            response_cleaner.process_markdown(core_features)
        )

        if config.config.md.image in [None, "", ImageOptions.ITMO_LOGO.value]:
            config.config.md.image = ImageOptions.ITMO_LOGO.value

        readme_md_content = MarkdownBuilder(config, context, temp_dir).build()

        FileHandler().write(output_file, readme_md_content)

        log_process_completion(output_file)


def log_repository_context(context: RepositoryContext) -> None:
    """Logs a snippet of the processed repository context data."""
    _logger.info(f"Total files analyzed: {len(context.files)}")
    _logger.info(f"Metadata extracted: {context.metadata}")
    _logger.info(f"Dependencies: {context.dependencies}")
    _logger.info(f"Languages: {context.language_counts}")


def log_process_completion(output_file: str) -> None:
    """Logs the completion of the README generation process."""
    _logger.info("README.md file generated successfully.")
    _logger.info(f"Output file saved @ {output_file}")
