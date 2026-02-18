import os

import tomli

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.context.files_contents import FileContext
from osa_tool.utils import extract_readme_content, logger, parse_folder_name, osa_project_root


class PromptBuilder:
    """
    PromptBuilder
    
    Builds prompts for repository analysis and documentation generation.  
    The class loads configuration and prompt templates, analyzes the repository
    structure, extracts metadata, and provides a set of methods to construct
    various prompts (pre‑analysis, core features, overview, getting started,
    deduplicated install/start, file summaries, PDF summaries, article
    overviews, content, algorithms, and README refinement).  It also offers
    utility functions for serializing file contexts and loading prompt
    definitions from TOML files.
    
    Attributes
    ----------
    config_loader
        The ConfigLoader instance passed to the constructor.
    config
        The configuration dictionary obtained from config_loader.
    readme_prompt_path
        Full path to the README prompt configuration file (prompts.toml).
    article_readme_prompt_path
        Full path to the article README prompt configuration file (prompts_article.toml).
    prompts
        Dictionary of prompts loaded from readme_prompt_path via load_prompts.
    prompts_article
        Dictionary of prompts loaded from article_readme_prompt_path via load_prompts.
    sourcerank
        Instance of SourceRank initialized with the same config_loader; used to analyze the repository tree.
    tree
        Repository tree structure obtained from sourcerank.tree.
    repo_url
        Repository URL extracted from the configuration (self.config.git.repository).
    metadata
        Repository metadata retrieved by load_data_metadata(self.repo_url). May be None if fetching fails.
    base_path
        Absolute path to the repository directory, constructed from the current working directory and the parsed folder name of repo_url.
    
    Methods
    -------
    get_prompt_preanalysis
        Builds a preanalysis prompt using the repository tree and README content.
    get_prompt_core_features
        Builds a core features prompt using project metadata, README content, and key files.
    get_prompt_overview
        Builds an overview prompt using metadata, README content, and extracted core features.
    get_prompt_getting_started
        Builds a getting started prompt using metadata, README content, and example files.
    get_prompt_deduplicated_install_and_start
        Builds a deduplicating prompt using Installation and Getting Started sections of README.
    get_prompt_files_summary
        Builds a files summary prompt using serialized file contents.
    get_prompt_pdf_summary
        Builds a PDF summary prompt using the provided PDF content.
    get_prompt_overview_article
        Builds an article overview prompt using metadata, file summary, and PDF summary.
    get_prompt_content_article
        Builds a content article prompt using metadata, key file content, and PDF summary.
    get_prompt_algorithms_article
        Builds an algorithms article prompt using metadata, file summary, and PDF summary.
    serialize_file_contexts
        Serializes a list of FileContext objects into a string.
    get_prompt_refine_readme
        Gets a refined prompt for updating the README.
    load_prompts
        Loads prompts from a TOML file and returns the specified section as a dictionary.
    """
    def __init__(self, config_loader: ConfigLoader):
        """
        Initializes the repository configuration and metadata loader.
        
        This constructor sets up the core attributes required for processing a repository:
        - Loads configuration and prompt files.
        - Instantiates a `SourceRank` object to analyze the repository tree.
        - Retrieves repository metadata from the configured source.
        - Determines the base path for the repository within the current working directory.
        
        Parameters
        ----------
        config_loader
            An instance of `ConfigLoader` that provides access to the parsed configuration.
        
        Attributes
        ----------
        config_loader
            The `ConfigLoader` instance passed to the constructor.
        config
            The configuration dictionary obtained from `config_loader`.
        readme_prompt_path
            Full path to the README prompt configuration file (`prompts.toml`).
        article_readme_prompt_path
            Full path to the article README prompt configuration file (`prompts_article.toml`).
        prompts
            Dictionary of prompts loaded from `readme_prompt_path` via `load_prompts`.
        prompts_article
            Dictionary of prompts loaded from `article_readme_prompt_path` via `load_prompts`.
        sourcerank
            Instance of `SourceRank` initialized with the same `config_loader`; used to analyze the repository tree.
        tree
            Repository tree structure obtained from `sourcerank.tree`.
        repo_url
            Repository URL extracted from the configuration (`self.config.git.repository`).
        metadata
            Repository metadata retrieved by `load_data_metadata(self.repo_url)`. May be `None` if fetching fails.
        base_path
            Absolute path to the repository directory, constructed from the current working directory and the parsed folder name of `repo_url`.
        
        Returns
        -------
        None
            This method does not return a value; it initializes instance attributes.
        """
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.readme_prompt_path = os.path.join(osa_project_root(), "config", "settings", "prompts.toml")
        self.article_readme_prompt_path = os.path.join(osa_project_root(), "config", "settings", "prompts_article.toml")
        self.prompts = self.load_prompts(self.readme_prompt_path)
        self.prompts_article = self.load_prompts(self.article_readme_prompt_path)
        self.sourcerank = SourceRank(config_loader)
        self.tree = self.sourcerank.tree

        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

    def get_prompt_preanalysis(self) -> str:
        """Builds a preanalysis prompt using the repository tree and README content."""
        try:
            formatted_prompt = self.prompts["preanalysis"].format(
                repository_tree=self.tree,
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build preanalysis prompt: {e}")
            raise

    def get_prompt_core_features(self, key_files: list[FileContext]) -> str:
        """Builds a core features prompt using project metadata, README content, and key files."""
        try:
            formatted_prompt = self.prompts["core_features"].format(
                project_name=self.metadata.name,
                metadata=self.metadata,
                readme_content=extract_readme_content(self.base_path),
                key_files_content=self.serialize_file_contexts(key_files),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build core features prompt: {e}")
            raise

    def get_prompt_overview(self, core_features: str) -> str:
        """Builds an overview prompt using metadata, README content, and extracted core features."""
        try:
            formatted_prompt = self.prompts["overview"].format(
                project_name=self.metadata.name,
                description=self.metadata.description,
                readme_content=extract_readme_content(self.base_path),
                core_features=core_features,
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build overview prompt: {e}")
            raise

    def get_prompt_getting_started(self, examples_files: list[FileContext]) -> str:
        """Builds a getting started prompt using metadata, README content, and example files."""
        try:
            formatted_prompt = self.prompts["getting_started"].format(
                project_name=self.metadata.name,
                readme_content=extract_readme_content(self.base_path),
                examples_files_content=self.serialize_file_contexts(examples_files),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build getting started prompt: {e}")
            raise

    def get_prompt_deduplicated_install_and_start(self, installation: str, getting_started: str) -> str:
        """Builds a deduplicating prompt using Installation and Getting Started sections of README."""
        try:
            formatted_prompt = self.prompts["deduplicate_sections"].format(
                installation=installation,
                getting_started=getting_started,
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build deduplicating prompt: {e}")
            raise

    def get_prompt_files_summary(self, files_content: list[FileContext]) -> str:
        """Builds a files summary prompt using serialized file contents."""
        try:
            formatted_prompt = self.prompts_article["file_summary"].format(
                files_content=self.serialize_file_contexts(files_content),
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build files summary prompt: {e}")
            raise

    def get_prompt_pdf_summary(self, pdf_content: str) -> str:
        """Builds a PDF summary prompt using the provided PDF content."""
        try:
            formatted_prompt = self.prompts_article["pdf_summary"].format(pdf_content=pdf_content)
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build PDF summary prompt: {e}")
            raise

    def get_prompt_overview_article(self, files_summary: str, pdf_summary: str) -> str:
        """Builds an article overview prompt using metadata, file summary, and PDF summary."""
        try:
            formatted_prompt = self.prompts_article["overview"].format(
                project_name=self.metadata.name,
                files_summary=files_summary,
                pdf_summary=pdf_summary,
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build overview prompt: {e}")
            raise

    def get_prompt_content_article(self, files_summary: str, pdf_summary: str) -> str:
        """Builds a content article prompt using metadata, key file content, and PDF summary."""
        try:
            formatted_prompt = self.prompts_article["content"].format(
                project_name=self.metadata.name,
                files_summary=files_summary,
                pdf_summary=pdf_summary,
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build content prompt: {e}")
            raise

    def get_prompt_algorithms_article(self, key_files: list[FileContext], pdf_summary: str) -> str:
        """Builds an algorithms article prompt using metadata, file summary, and PDF summary."""
        try:
            formatted_prompt = self.prompts_article["algorithms"].format(
                project_name=self.metadata.name,
                files_content=key_files,
                pdf_summary=pdf_summary,
                readme_content=extract_readme_content(self.base_path),
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build algorithms prompt: {e}")
            raise

    @staticmethod
    def serialize_file_contexts(files: list[FileContext]) -> str:
        """
        Serializes a list of FileContext objects into a string.

        Args:
            files (list[FileContext]): A list of FileContext objects representing files.

        Returns:
            str: A string representing the serialized file data.
                Each section includes the file's name, path, and content.
        """
        return "\n\n".join(f"### {f.name} ({f.path})\n{f.content}" for f in files)

    def get_prompt_refine_readme(self, new_readme_sections: dict) -> str:
        """
        Get a refined prompt for updating the README.
        
        This method constructs a prompt for refining a README file by formatting a template stored in the instance's prompts dictionary. It extracts the current README content from the base path and incorporates the new sections provided.
        
        Args:
            new_readme_sections: A dictionary containing the new sections to be added or updated in the README.
        
        Returns:
            str: The formatted prompt string ready to be used for refining the README.
        
        Raises:
            Exception: If building the prompt fails, the error is logged and re‑raised.
        """
        try:
            formatted_prompt = self.prompts["refine"].format(
                old_readme=extract_readme_content(self.base_path), new_readme_sections=new_readme_sections
            )
            return formatted_prompt
        except Exception as e:
            logger.error(f"Failed to build refine readme prompt: {e}")
            raise

    @staticmethod
    def load_prompts(path: str, section: str = "prompts") -> dict:
        """
        Load prompts from a TOML file and return the specified section as a dictionary.

        Args:
            path (str): Path to the TOML file.
            section (str): Section inside the TOML to extract (default: "prompts").

        Returns:
            dict: Dictionary with prompts from the specified section.
        """
        if not os.path.exists(path):
            logger.error(f"Prompts file {path} not found.")
            raise FileNotFoundError(f"Prompts file {path} not found.")

        with open(path, "rb") as f:
            toml_data = tomli.load(f)

        if section not in toml_data:
            logger.error(f"Section '{section}' not found in {path}.")
            raise KeyError(f"Section '{section}' not found in {path}.")

        return toml_data[section]
