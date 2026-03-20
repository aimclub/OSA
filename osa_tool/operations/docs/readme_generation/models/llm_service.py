import os

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.operations.docs.readme_generation.context.files_contents import FileProcessor
from osa_tool.operations.docs.readme_generation.utils import extract_example_paths
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import parse_folder_name, extract_readme_content


class LLMClient:
    """
    LLMClient class for generating and refining repository documentation using language models.
    
        This class serves as a client for interacting with language models to analyze repositories,
        extract key information, generate documentation sections, and refine README content. It
        integrates configuration management, repository analysis tools, and model handling to
        produce comprehensive documentation artifacts.
    
        Class Fields Initialized:
            config_manager: Configuration manager instance for accessing various settings and configurations.
            model_settings: Model configuration settings for readme-related tasks.
            metadata: Metadata about the repository being processed.
            prompts: Loader for prompt templates used in documentation generation.
            model_handler: Model handler instance built from model settings for processing tasks.
            sourcerank: SourceRank instance for repository analysis.
            tree: Tree structure from SourceRank analysis.
            repo_url: URL of the Git repository being processed.
            base_path: Local file system path where the repository is located.
            readme_content: Content extracted from the repository's README file.
    
        Methods:
            get_responses: Extracts core features, overview, and optionally a Getting Started section.
            get_responses_article: Generates an article-style summary of the repository.
            get_key_files: Identifies key files from the project repository using model analysis.
            get_getting_started: Generates Getting Started section using README, examples and docs.
            get_citation_from_readme: Extracts a citation string from the repository's README content.
            refine_readme: Refines a generated README by applying three sequential refinement steps.
            clean: Cleans a README string through a three-step LLM-powered cleaning pipeline.
            get_article_name: Extracts the article name from provided PDF content.
    """

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        """
        Initializes the LLMClient instance with configuration and repository metadata.
        
        This constructor sets up the necessary components for processing repository
        documentation, including configuration management, model handling, and
        repository analysis tools.
        
        Args:
            config_manager: Configuration manager providing access to settings,
                prompts, and git configuration.
            metadata: Metadata about the repository being processed.
        
        Class Fields Initialized:
            config_manager (ConfigManager): Configuration manager instance for
                accessing various settings and configurations.
            model_settings (ModelSettings): Model configuration settings for
                readme-related tasks, retrieved from the config manager.
            metadata (RepositoryMetadata): Metadata about the repository being
                processed.
            prompts (PromptLoader): Loader for prompt templates used in
                documentation generation, retrieved from the config manager.
            model_handler (ModelHandler): Model handler instance built from
                the readme model settings for processing tasks.
            sourcerank (SourceRank): SourceRank instance for repository analysis,
                initialized with the config manager.
            tree: Tree structure from the SourceRank analysis, accessed from the
                sourcerank instance.
            repo_url (str): URL of the Git repository being processed, retrieved
                from the git settings in the config manager.
            base_path (str): Local file system path where the repository is
                located, constructed by joining the current working directory with
                a folder name parsed from the repository URL.
            readme_content (str): Content extracted from the repository's README
                file, or a default message if no README is found. The extraction
                searches for common README filenames (prioritizing Markdown and
                English versions) within the base_path.
        """
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("readme")
        self.metadata = metadata
        self.prompts = self.config_manager.get_prompts()
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.sourcerank = SourceRank(self.config_manager)
        self.tree = self.sourcerank.tree

        self.repo_url = self.config_manager.get_git_settings().repository
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.readme_content = extract_readme_content(self.base_path)

    def get_responses(self) -> tuple[str, str, str]:
        """
        Extracts core features, overview, and optionally a Getting Started section from the repository.
        
        This method orchestrates the generation of a README-style summary by analyzing the repository's key files, metadata, and existing README content. It uses a language model to produce structured outputs for each section. The process is sequential: first core features are generated, then the overview (which incorporates the core features), and finally a Getting Started section if example files are available.
        
        Why:
        Automating this summary generation ensures consistent, high-quality documentation that synthesizes information from across the repository, reducing manual effort for maintainers and improving project accessibility for new users.
        
        Args:
            None. Uses instance attributes configured during the LLMClient initialization, including:
                - config_manager: Configuration settings.
                - metadata: Project metadata (name, description, etc.).
                - readme_content: Existing README file content.
                - prompts: Template prompts for each section.
                - model_handler: Handler for LLM communication and response parsing.
        
        Returns:
            tuple[str, str, str]: A tuple containing three strings in order:
                - core_features: A description of the main functionalities and capabilities of the project, parsed from the LLM's JSON response.
                - overview: A general description and project context, validated as a string from the LLM's JSON response under the key "overview".
                - getting_started: A setup or usage guide if examples are available; otherwise, an empty string or None. This is generated by a separate helper method.
        """
        logger.info("Started generating README-style summary.")
        key_files = self.get_key_files()
        key_files_content = FileProcessor(self.config_manager, key_files).process_files()

        logger.info("Generating core features of the project...")
        core_features = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.core_features"),
                project_name=self.metadata.name,
                metadata=self.metadata,
                readme_content=self.readme_content,
                key_files_content=FileProcessor.serialize_file_contexts(key_files_content),
            ),
            parser=lambda raw: JsonProcessor.parse(raw),
        )

        logger.info("Generating project overview...")
        overview = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.overview"),
                project_name=self.metadata.name,
                description=self.metadata.description,
                readme_content=self.readme_content,
                core_features=core_features,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="overview", expected_type=str),
        )

        getting_started = self.get_getting_started()

        logger.info("README-style summary generation completed.")
        return core_features, overview, getting_started

    def get_responses_article(self, article: str) -> tuple[str, str, str, str]:
        """
        Generates an article-style summary of the repository based on key files and associated PDF documentation.
        
        The method synthesizes an overview, content description, algorithm explanation, and a getting started guide by analyzing the project's key source files, README, and a provided PDF document. This is useful for creating comprehensive, narrative-style documentation that contextualizes the project within its research or descriptive background.
        
        Args:
            article: Path or URL to a research or descriptive PDF document associated with the project. The method validates and, if necessary, downloads the PDF before extracting its text content.
        
        Returns:
            tuple[str, str, str, str]: A tuple containing four strings in order:
             - overview: General description and project context, generated from the PDF summary and README.
             - content: Detailed content section based on summaries of key files and the PDF.
             - algorithms: Description of algorithms used, derived from key file contents and the PDF summary.
             - getting_started: A practical guide for new users, synthesized from the repository's README and example files.
        
        Why:
            This structured summary helps users and researchers quickly understand the project's purpose, implementation, and usage by combining insights from both the codebase and external documentation.
        """
        logger.info("Started generating Article-style summary.")
        key_files = self.get_key_files()
        key_files_content = FileProcessor(self.config_manager, key_files).process_files()

        logger.info("Generating summary of key files...")
        files_summary = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme_article.file_summary"),
                files_content=FileProcessor.serialize_file_contexts(key_files_content),
                readme_content=self.readme_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="file_summary", expected_type=str),
        )

        path_to_pdf = get_pdf_path(article)
        pdf_content = PdfParser(path_to_pdf).data_extractor()

        logger.info("Generating summary of PDF content...")
        pdf_summary = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(self.prompts.get("readme_article.pdf_summary"), pdf_content=pdf_content),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="pdf_summary", expected_type=str),
        )

        logger.info("Generating project overview from combined sources...")
        overview = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme_article.overview"),
                project_name=self.metadata.name,
                pdf_summary=pdf_summary,
                readme_content=self.readme_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="overview", expected_type=str),
        )

        logger.info("Generating content section...")
        content = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme_article.content"),
                project_name=self.metadata.name,
                pdf_summary=pdf_summary,
                files_summary=files_summary,
                readme_content=self.readme_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="content", expected_type=str),
        )

        logger.info("Generating algorithm description...")
        algorithms = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme_article.algorithms"),
                project_name=self.metadata.name,
                files_content=FileProcessor.serialize_file_contexts(key_files_content),
                pdf_summary=pdf_summary,
                readme_content=self.readme_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="algorithms", expected_type=str),
        )

        getting_started = self.get_getting_started()

        logger.info("Article-style summary generation completed.")
        return overview, content, algorithms, getting_started

    def get_key_files(self) -> list:
        """
        Identifies key files from the project repository using model analysis.
        
        This method prompts an LLM to analyze the repository's structure and README content to determine which files are most important or central to the project. The analysis helps focus subsequent documentation and enhancement operations on critical parts of the codebase.
        
        Args:
            None.
        
        Returns:
            A list of strings representing the paths or names of the identified key files. If the analysis fails or returns no data, an empty list is returned.
        """
        data = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.preanalysis"),
                repository_tree=self.tree,
                readme_content=self.readme_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="key_files", expected_type=list),
        )
        return data or []

    def get_getting_started(self) -> str | None:
        """
        Attempt to generate a "Getting Started" section for the project by synthesizing information from the repository's README, examples, and documentation files.
        
        This method orchestrates the extraction and processing of example files, then uses a language model to generate a concise "Getting Started" guide. The generation is prompted with structured content from the project's README and processed example files to ensure the output is relevant and practical.
        
        Args:
            None. Uses instance attributes configured during the LLMClient initialization.
        
        Returns:
            The generated "Getting Started" text as a string, or None if the process fails. The text is parsed from the LLM's JSON response, specifically from the key "getting_started".
        
        Why:
            Automating this section improves project accessibility by providing new users with immediate, context-aware guidance synthesized from the project's own documentation and examples, reducing the manual effort for maintainers.
        """
        logger.info("Attempting to generate Getting Started section...")
        examples_files = extract_example_paths(self.tree)
        examples_content = FileProcessor(self.config_manager, examples_files).process_files()
        return self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.getting_started"),
                project_name=self.metadata.name,
                readme_content=self.readme_content,
                examples_files_content=FileProcessor.serialize_file_contexts(examples_content),
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="getting_started"),
        )

    def get_citation_from_readme(self) -> str:
        """
        Extracts a citation string from the repository's README content using an LLM.
        
        This method sends the README content to a language model, prompting it to identify and return a citation. The model's response is parsed to extract a string value. The method retries on parsing errors up to a configured maximum number of attempts.
        
        Args:
            readme: The content of the repository's README file, provided as a string. This is passed into the prompt template.
        
        Returns:
            str: The citation text extracted from the README.
        
        Raises:
            JsonParseError: If the LLM response cannot be parsed as valid JSON after all retry attempts.
            ValidationError: If the parsed content fails pydantic validation after all retries.
        """
        logger.info("Detecting citations in README...")
        return self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.citation"),
                readme=self.readme_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="citation", expected_type=str),
        )

    def refine_readme(self, generated_readme: str) -> str:
        """
        Refines a generated README by applying three sequential refinement steps using an LLM.
        
        Args:
            generated_readme: The initial README content to be refined.
        
        Returns:
            The final refined README content after three processing steps.
        
        Why:
            The method performs three distinct refinement steps to progressively improve the README quality. Each step uses a different prompt template (readme.refine_step1, readme.refine_step2, readme.refine_step3) to guide the LLM in enhancing the content. The refinement is sequential, where the output of each step becomes the input for the next, allowing for layered improvements such as structural organization, detail enhancement, and final polishing.
        """
        logger.info("Refining README files...")
        refine_step1 = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.refine_step1"),
                old_readme=self.readme_content,
                new_readme=generated_readme,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="readme", expected_type=str),
        )
        refine_step2 = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.refine_step2"),
                readme=refine_step1,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="readme", expected_type=str),
        )
        refine_step3 = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.refine_step3"),
                readme=refine_step2,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="readme", expected_type=str),
        )
        return refine_step3

    def clean(self, readme: str) -> str:
        """
        Cleans a README string through a three-step LLM-powered cleaning pipeline.
        
        Each step uses a specific prompt (readme.clean_step1, readme.clean_step2, readme.clean_step3) to progressively refine the content. The LLM's response for each step is parsed as JSON to extract a string value under the key "readme". This structured extraction ensures the output is consistently formatted and free of surrounding text or formatting artifacts from the model.
        
        Args:
            readme: The raw README content string to be cleaned.
        
        Returns:
            The cleaned README content string after three sequential processing steps.
        """
        logger.info("Cleaning README...")
        clean_step1 = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.clean_step1"),
                readme=readme,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="readme", expected_type=str),
        )
        clean_step2 = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.clean_step2"),
                readme=clean_step1,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="readme", expected_type=str),
        )
        clean_step3 = self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme.clean_step3"),
                readme=clean_step2,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="readme", expected_type=str),
        )
        return clean_step3

    def get_article_name(self, pdf_content: str) -> str:
        """
        Extracts the article name from the provided PDF content using an LLM.
        
        The method uses a specific prompt template (key: "readme_article.article_name_extraction") to instruct the LLM. The LLM's response is parsed as JSON to extract a value under the key "article_name", which is expected to be a string. If parsing or validation fails, the underlying handler will retry the request up to a configured maximum number of attempts.
        
        Args:
            pdf_content: The raw text content extracted from a PDF file.
        
        Returns:
            The extracted article name as a string.
        
        Raises:
            JsonParseError: If JSON parsing fails after all retry attempts.
            ValidationError: If pydantic validation fails after all retry attempts.
            PromptBuilderError: If an error occurs while rendering the prompt template.
        """
        logger.info("Getting article name from pdf...")
        return self.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                self.prompts.get("readme_article.article_name_extraction"),
                pdf_content=pdf_content,
            ),
            parser=lambda raw: JsonProcessor.parse(raw, expected_key="article_name", expected_type=str),
        )
