from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.generator.base_builder import MarkdownBuilderBase


class MarkdownBuilderArticle(MarkdownBuilderBase):
    """
    Builds each section of the README Markdown file for article-like repositories.
    """


    def __init__(
        self,
        config_manager: ConfigManager,
        metadata: RepositoryMetadata,
        overview: str = None,
        content: str = None,
        algorithms: str = None,
        getting_started: str = None,
    ):
        """
        Initializes a new instance of the MarkdownBuilderArticle class with configuration, metadata, and content details.
        
        Args:
            config_manager: The manager responsible for handling configuration settings, passed to the parent class for shared initialization.
            metadata: Metadata information related to the repository, passed to the parent class for shared initialization.
            overview: A brief summary or overview of the repository; passed to the parent class.
            content: The primary content or body text; stored as an instance attribute.
            algorithms: Information or documentation regarding the algorithms used; stored as an instance attribute.
            getting_started: Instructions or guide for getting started with the repository; passed to the parent class.
        
        Attributes:
            _content: Stores the primary content or body text provided during initialization.
            _algorithms: Stores the information regarding algorithms provided during initialization.
        
        Why:
            This constructor extends a parent class to handle article-specific content (like detailed content and algorithm descriptions) while delegating common initialization (configuration, metadata, overview, and getting-started sections) to the superclass. This separation allows the class to focus on managing the core article content within the broader documentation generation pipeline.
        """
        super().__init__(config_manager, metadata, overview=overview, getting_started=getting_started)
        self._content = content
        self._algorithms = algorithms

    @property
    def content(self) -> str:
        """
        Generates the README Repository Content section.
        
        This property returns the formatted content for the "Repository Content" section of the README.
        If the internal content data (`self._content`) is empty or not set, an empty string is returned.
        Otherwise, it formats the content using a predefined template (`self._template["content"]`).
        
        Returns:
            The formatted "Repository Content" section as a string, or an empty string if no content is available.
        """
        if not self._content:
            return ""
        return self._template["content"].format(self._content)

    @property
    def algorithms(self) -> str:
        """
        Generates the README Algorithms section.
        
        This property returns a formatted string for the Algorithms section of the README,
        using predefined template formatting. If no algorithms data is present, it returns
        an empty string to avoid unnecessary sections in the output.
        
        Returns:
            The formatted Algorithms section as a string, or an empty string if there are
            no algorithms to document.
        """
        if not self._algorithms:
            return ""
        return self._template["algorithms"].format(self._algorithms)

    @property
    def toc(self) -> str:
        """
        Generates a table of contents for the markdown document.
        
        This property organizes the predefined sections of the article—Content, Algorithms, Installation, Getting Started, License, and Citation—into a dictionary mapping each section title to its corresponding content property. It then passes this dictionary to a helper method (`table_of_contents`) which formats the sections into a structured, navigable table of contents string. This centralized approach ensures the TOC is consistently generated from the article's core sections.
        
        Returns:
            str: A formatted string representing the table of contents, ready for insertion into the markdown document.
        """
        sections = {
            "Content": self.content,
            "Algorithms": self.algorithms,
            "Installation": self.installation,
            "Getting Started": self.getting_started,
            "License": self.license,
            "Citation": self.citation,
        }
        return self.table_of_contents(sections)

    def build(self) -> str:
        """
        Builds the complete README.md content by concatenating all predefined sections in order.
        
        The method assembles the final README text by joining the individual section strings
        that have been previously generated and stored as instance attributes. This ensures
        a consistent structure and proper ordering of sections in the output document.
        
        Args:
            None
        
        Returns:
            The full README.md content as a single string, with sections separated by newlines.
        """
        readme_contents = [
            self.header,
            self.overview,
            self.toc,
            self.content,
            self.algorithms,
            self.installation,
            self.getting_started,
            self.examples,
            self.documentation,
            self.license,
            self.citation,
        ]

        return "\n".join(readme_contents)
