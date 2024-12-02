import tempfile
import os

from readmegen.config.constants import ImageOptions
from readmegen.config.settings import ConfigLoader

from readmegen.generators.builder import MarkdownBuilder
from readmegen.ingestion.models import RepositoryContext
from readmegen.ingestion.pipeline import RepositoryProcessor

from readmegen.models.factory import ModelFactory
from readmegen.postprocessor import response_cleaner
from readmegen.readers.git.repository import load_data
from readmegen.utils.file_handler import FileHandler


def readme_generator(config: ConfigLoader, output_file: str) -> None:
    """Processes the repository and builds the README file."""

    with tempfile.TemporaryDirectory() as temp_dir:

        repo_path = load_data(config.config.git.repository, temp_dir)
        print("load finished")

        processor: RepositoryProcessor = RepositoryProcessor(config=config)
        print("repoProcess finished")
        context: RepositoryContext = processor.process_repository(repo_path=repo_path)
        print("repoContext finished")

        llm = ModelFactory.get_backend(config, context)
        print("starting post responses")
        responses = llm.batch_request()
        print("responses ready")
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

        if config.config.md.image in [None, ""]:
            config.config.md.image = ImageOptions.ITMO_LOGO.value

        readme_md_content = MarkdownBuilder(
            config, context, temp_dir
        ).build()

        FileHandler().write(output_file, readme_md_content)


file_to_save = os.path.join(os.getcwd(), "examples", "README.md")
readme_generator(ConfigLoader(), file_to_save)
