import os

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.docs.readme_generation.generator.builder import MarkdownBuilder
from osa_tool.operations.docs.readme_generation.generator.builder_article import MarkdownBuilderArticle
from osa_tool.operations.docs.readme_generation.models.llm_service import LLMClient
from osa_tool.operations.docs.readme_generation.utils import remove_extra_blank_lines, save_sections
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import parse_folder_name


class ReadmeAgent:
    """
    ReadmeAgent generates and manages README.md documentation for repositories.
    
        This class handles the creation, refinement, and structuring of repository documentation
        by leveraging language models and repository metadata. It supports both default README
        generation and article-style documentation with customizable content.
    
        Attributes:
            config_manager: Configuration manager instance for accessing settings.
            article: Optional article content for documentation inclusion.
            refine_readme: Flag indicating README refinement preference.
            metadata: Repository metadata for context-aware documentation.
            repo_url: URL of the Git repository from configuration.
            repo_path: Local filesystem path where repository is/will be located.
            file_to_save: Full path to the README.md file to be generated/updated.
            llm_client: Client for interacting with language models.
            events: List to track documentation generation events.
    
        Methods:
            __init__: Initializes the agent with configuration, metadata, and optional parameters.
            generate_readme: Orchestrates the README generation process and returns operation results.
            default_readme: Creates a standard README structure using LLM-generated content.
            article_readme: Produces an article-style README by processing documentation through LLM.
    """


    def __init__(
        self,
        config_manager: ConfigManager,
        metadata: RepositoryMetadata,
        attachment: str | None = None,
        refine_readme: bool = False,
    ):
        """
        Initializes the ReadmeAgent instance with configuration, metadata, and optional parameters.
        
        Sets up the necessary components for repository documentation generation, including the LLM client, file paths, and event tracking. The agent prepares to generate or update a README.md file for the specified Git repository.
        
        Args:
            config_manager: Manages configuration settings, including Git repository information.
            metadata: Contains repository metadata used to guide context-aware documentation generation.
            attachment: Optional article content to include in the documentation. Stored as `self.article`.
            refine_readme: Flag indicating whether to refine an existing README.md file instead of generating a new one from scratch.
        
        Why:
        - The repository URL from the configuration is used to derive a local folder name (via `parse_folder_name`) and construct the local repository path.
        - The `file_to_save` is set to "README.md" inside that local path, defining the target file for documentation operations.
        - An LLMClient is initialized with the configuration and metadata to enable language model interactions during documentation generation.
        - An empty event list is created to track documentation generation steps and outcomes for logging or monitoring.
        
        Initializes the following instance attributes:
            config_manager (ConfigManager): Configuration manager instance for accessing settings.
            article (str | None): Optional article content for documentation inclusion.
            refine_readme (bool): Flag indicating README refinement preference.
            metadata (RepositoryMetadata): Repository metadata for context-aware documentation.
            repo_url (str): URL of the Git repository, obtained from the configuration's Git settings.
            repo_path (str): Local filesystem path where the repository is or will be located, derived from the current working directory and the parsed folder name.
            file_to_save (str): Full path to the README.md file to be generated or updated.
            llm_client (LLMClient): Client for interacting with language models, configured with the agent's settings and metadata.
            events (list[OperationEvent]): List to track documentation generation events.
        """
        self.config_manager = config_manager
        self.article = attachment
        self.refine_readme = refine_readme
        self.metadata = metadata
        self.repo_url = self.config_manager.get_git_settings().repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.file_to_save = os.path.join(self.repo_path, "README.md")
        self.llm_client = LLMClient(self.config_manager, self.metadata)
        self.events: list[OperationEvent] = []

    def generate_readme(self) -> dict:
        """
        Generate README.md file for the repository.
        
        The method orchestrates the creation of a README file, choosing between a default structure and an article‑style format based on whether an associated article (PDF documentation) is provided. It then optionally refines and cleans the content using an LLM, saves the final Markdown to disk, and returns a standardized report of the operation.
        
        WHY: This method centralizes the README generation workflow, ensuring consistent formatting and providing optional AI‑driven enhancement to improve clarity and completeness. The choice between default and article‑style READMEs allows the tool to adapt to different documentation needs—standard project overviews versus in‑depth, narrative‑driven documentation.
        
        Returns:
            dict: Standardized operation output containing:
                - result: A dictionary with details about the generated README, including the filename, full save path, and whether refinement was applied. If generation fails, result is None.
                - events: List of OperationEvent objects tracking the steps performed (e.g., GENERATED, REFINED, FAILED) and any error information.
        """
        logger.info("Started generating README.md. Processing the repository: %s", self.repo_url)

        try:
            if self.article is None:
                builder = self.default_readme()
            else:
                builder = self.article_readme()

            readme_content = builder.build()

            self.events.append(OperationEvent(kind=EventKind.GENERATED, target="README.md"))

            if self.refine_readme:
                readme_content = self.llm_client.refine_readme(readme_content)
                self.events.append(OperationEvent(kind=EventKind.REFINED, target="README.md"))

            if self.article is None:
                readme_content = self.llm_client.clean(readme_content)

            save_sections(readme_content, self.file_to_save)
            remove_extra_blank_lines(self.file_to_save)
            logger.info(f"README.md successfully generated in folder {self.repo_path}")
            return {
                "result": {
                    "file": "README.md",
                    "path": self.file_to_save,
                    "refined": self.refine_readme,
                },
                "events": self.events,
            }
        except Exception as e:
            logger.error("Error while generating: %s", repr(e), exc_info=True)
            self.events.append(
                OperationEvent(
                    kind=EventKind.FAILED,
                    target="README.md",
                    data={
                        "reason": "generation_error",
                        "error": repr(e),
                    },
                )
            )

            return {
                "result": None,
                "events": self.events,
            }

    def default_readme(self) -> MarkdownBuilder:
        """
        Generates a default README structure by retrieving content from the language model client.
        
        This method fetches the core features, project overview, and getting started instructions from the LLM client and uses them to initialize a MarkdownBuilder instance. The content is sourced from the repository's key files and processed by the model to produce structured documentation sections.
        
        Args:
            self: The ReadmeAgent instance.
        
        Returns:
            MarkdownBuilder: An object configured to build the README file using the retrieved content and project metadata. The builder is initialized with the project configuration, metadata, and the three extracted content sections.
        """
        responses = self.llm_client.get_responses()
        core_features, overview, getting_started = responses
        return MarkdownBuilder(self.config_manager, self.metadata, overview, core_features, getting_started)

    def article_readme(self) -> MarkdownBuilderArticle:
        """
        Generates a structured article-style README for the repository by processing associated documentation through an LLM.
        
        This method orchestrates the creation of an article‑style README by first obtaining structured content from the LLM based on the associated PDF documentation, then packaging that content into a builder object. The article‑style format is intended to provide a narrative, in‑depth overview of the project, suitable for research or detailed technical introductions.
        
        Args:
            self: The instance of the ReadmeAgent class.
        
        Returns:
            MarkdownBuilderArticle: An object configured to build the article README. It is initialized with the generated overview, content, algorithms, and getting started sections, along with the configuration manager and repository metadata.
        """
        responses = self.llm_client.get_responses_article(self.article)
        overview, content, algorithms, getting_started = responses
        return MarkdownBuilderArticle(
            self.config_manager, self.metadata, overview, content, algorithms, getting_started
        )
