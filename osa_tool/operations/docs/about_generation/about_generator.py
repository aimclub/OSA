import os
import re
from typing import List

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import extract_readme_content, parse_folder_name

HOMEPAGE_KEYS = [
    "documentation",
    "doc",
    "docs",
    "about",
    "homepage",
    "wiki",
    "readthedocs",
    "netlify",
]


class AboutGenerator:
    """
    Generates Git repository About section content.
    """


    def __init__(self, config_manager: ConfigManager, git_agent: GitAgent):
        """
        Initializes the AboutGenerator class instance with configuration and Git-related components.
        
        This constructor sets up the necessary dependencies and initializes various attributes used throughout the class for repository analysis and documentation generation. It prepares the instance by loading model settings, prompts, and repository metadata, and establishes paths and content needed for subsequent operations.
        
        Args:
            config_manager: Manages configuration settings including model settings, prompts, and Git repository information.
            git_agent: Provides Git repository metadata and topic validation functionality.
        
        Class Fields Initialized:
            config_manager: Configuration manager for accessing settings and prompts.
            model_settings: Model configuration for general tasks, retrieved from the config_manager.
            prompts: Loader for prompt templates used in documentation generation.
            model_handler: Handler for model operations, built using the general model settings.
            repo_url: URL of the Git repository being analyzed, obtained from the Git settings in the configuration.
            metadata: Git repository metadata provided by the GitAgent.
            base_path: Local file system path where the repository is expected to be located. It is derived by joining the current working directory with a folder name parsed from the repository URL.
            readme_content: Content extracted from the repository's README file, or a default message if no README is found. The extraction prioritizes common README filenames and formats.
            validate_topics: Function for validating repository topics, provided by the GitAgent.
            _content: Placeholder for processed content, initially set to None. This is intended to store analysis results or intermediate data.
            events: List to track operation events (such as errors or milestones) during repository analysis.
        """
        self.config_manager = config_manager
        self.model_settings = config_manager.get_model_settings("general")
        self.prompts = self.config_manager.get_prompts()
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.repo_url = self.config_manager.get_git_settings().repository
        self.metadata = git_agent.metadata
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.readme_content = extract_readme_content(self.base_path)
        self.validate_topics = git_agent.validate_topics
        self._content: dict | None = None
        self.events: list[OperationEvent] = []

    def generate_about_content(self) -> dict:
        """
        Generate About section content and return structured result with events.
        
        This method orchestrates the generation of the 'About' section fields (description, homepage, topics) for a repository. It ensures generation is performed only once by caching the result (`self._content`). If content has already been generated, a warning is logged and the cached result is returned. Otherwise, it calls helper methods to generate each field, stores the combined result, and records an operation event detailing what was generated.
        
        Returns:
            dict:
                - result: A dictionary containing the generated 'About' section fields:
                    - description: A concise repository description.
                    - homepage: The detected homepage URL.
                    - topics: A list of repository topics.
                - events: A list of OperationEvent objects, appended with a new event of kind EventKind.GENERATED for the "about" target, containing data about the generation outcomes (e.g., whether description/homepage were produced, topics count).
        """
        if self._content is not None:
            logger.warning("About section content already generated. Skipping generation.")
            return {
                "result": self._content,
                "events": self.events,
            }
        if self._content is None:
            logger.info("Generating 'About' section...")

            description = self._generate_description()
            homepage = self._detect_homepage()
            topics = self._generate_topics()

            self._content = {
                "description": description,
                "homepage": homepage,
                "topics": topics,
            }

            self.events.append(
                OperationEvent(
                    kind=EventKind.GENERATED,
                    target="about",
                    data={
                        "description": bool(description),
                        "homepage": bool(homepage),
                        "topics_count": len(topics),
                    },
                )
            )

        return {
            "result": self._content,
            "events": self.events,
        }

    def get_about_content(self) -> dict:
        """
        Returns the generated About section content.
        
        This method ensures the About content is generated exactly once by caching the result.
        If the content has not been generated yet (`self._content` is `None`), it triggers the generation process via `generate_about_content`. The cached content is then returned.
        
        Returns:
            dict: A dictionary containing the generated 'About' section fields:
                - description: A concise repository description.
                - homepage: The detected homepage URL.
                - topics: A list of repository topics.
        """
        if self._content is None:
            self.generate_about_content()
        return self._content

    def get_about_section_message(self) -> str:
        """
        Returns a formatted message for the Git About section.
        
        This method generates a user-friendly message containing the repository's description, homepage, and topics, formatted for direct use in a Git repository's About section. It ensures the underlying content is generated (if not already cached) and logs the process.
        
        Why:
        - The message is intended to guide the user on what information to add to their repository's About section.
        - It formats the cached content into a clear, bulleted list for easy copying and review.
        
        Returns:
            A string containing the formatted message, with placeholders for the description, homepage, and topics.
        """
        logger.info("Started generating About section content.")
        if self._content is None:
            self.generate_about_content()

        about_section_content = (
            "You can add the following information to the `About` section of your Git repository:\n"
            f"- Description: {self._content['description']}\n"
            f"- Homepage: {self._content['homepage']}\n"
            f"- Topics: {', '.join(f'`{topic}`' for topic in self._content['topics'])}\n"
            "\nPlease review and add them to your repository.\n"
        )
        logger.debug(f"Generated About section content: {about_section_content}")
        logger.info("Finished generating About section content.")
        return about_section_content

    def _generate_description(self) -> str:
        """
        Generates a repository description based on README content.
        
        WHY: This method is used to automatically create a concise description for a repository when one is not already present in the metadata. It leverages the README content as a source, as READMEs often contain introductory information suitable for summarizing the repository's purpose.
        
        If a description already exists in the metadata, generation is skipped to avoid overwriting existing information. If no README content is available, generation cannot proceed.
        
        The generated description is truncated to a maximum length (350 characters) to ensure it remains concise. If an error occurs during the generation process, an empty string is returned.
        
        Args:
            None.
        
        Returns:
            str: A repository description (up to 350 characters) if successfully generated; the existing metadata description if one already exists; or an empty string if README content is unavailable or an error occurs.
        """
        if self.metadata and self.metadata.description:
            logger.warning("Description already exists in metadata. Skipping generation.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SKIPPED,
                    target="about.description",
                    data={"reason": "already_exists"},
                )
            )
            return self.metadata.description

        if not self.readme_content:
            logger.warning("No README content found. Cannot generate description.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SKIPPED,
                    target="about.description",
                    data={"reason": "no_readme"},
                )
            )
            return ""

        prompt = PromptBuilder.render(
            self.prompts.get("about_section.description"),
            readme_content=self.readme_content,
        )

        try:
            description = self.model_handler.send_request(prompt)
            logger.debug(f"Generated description: {description}")
            return description[:350]
        except Exception as e:
            logger.error("Error generating description: %s", e)
            self.events.append(
                OperationEvent(
                    kind=EventKind.FAILED,
                    target="about.description",
                    data={"error": str(e)},
                )
            )
            return ""

    def _generate_topics(self, amount: int = 7) -> List[str]:
        """
        Generates Git repository topics based on README content.
        
        This method uses the README content to suggest new topics via an LLM, then combines them with any existing topics already present in the repository metadata. It ensures the total number of topics does not exceed the specified maximum and handles errors gracefully by returning the existing topics.
        
        Args:
            amount: Maximum number of topics to return (default 7, max 20). If existing topics already meet or exceed this amount, no new topics are generated.
        
        Returns:
            A list of up to `amount` topics, or an empty list if none can be generated. The list includes both existing and newly generated topics, deduplicated and formatted (lowercased, spaces replaced with hyphens). If generation fails or the amount exceeds the maximum, the existing topics are returned unchanged.
        
        Why:
        - The method first checks existing topics to avoid unnecessary LLM calls when enough topics are already present.
        - It enforces a maximum of 20 topics because Git hosting platforms (like GitHub) typically impose a limit on the number of topics per repository.
        - Topics are formatted to ensure consistency with common repository tagging conventions (lowercase, hyphen-separated).
        - Errors during LLM request or processing are logged and handled by returning the existing topics, ensuring the repository metadata is not lost.
        """
        logger.info(f"Generating up to {amount} topics...")

        existing_topics = getattr(self.metadata, "topics", []) or []

        if amount > 20:
            logger.critical("Maximum amount of topics is 20.")
            return existing_topics

        if len(existing_topics) >= amount:
            logger.warning(f"{amount} topics already exist in the metadata. Skipping generation.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SKIPPED,
                    target="about.topics",
                    data={"reason": "enough_existing"},
                )
            )
            return existing_topics

        prompt = PromptBuilder.render(
            self.prompts.get("about_section.topics"),
            readme_content=self.readme_content,
            amount=amount,
            topics=existing_topics,
        )

        try:
            response = self.model_handler.send_request(prompt)
            topics = [topic.strip().lower().replace(" ", "-") for topic in response.split(",") if topic.strip()]
            logger.debug(f"Generated topics from LLM: {topics}")
            validated_topics = self.validate_topics(topics)
            return list({*existing_topics, *validated_topics})
        except Exception as e:
            logger.error(f"Error generating topics: {e}")
            self.events.append(
                OperationEvent(
                    kind=EventKind.FAILED,
                    target="about.topics",
                    data={"error": str(e)},
                )
            )
            return existing_topics

    def _detect_homepage(self) -> str:
        """
        Detects the homepage URL for a project.
        
        The method first checks if a homepage is already present in the project metadata; if so, it logs a skip event and returns that URL. Otherwise, it extracts URLs from the README content, analyzes them to identify the most relevant ones, and selects a homepage candidate. The selection prioritizes URLs containing common homepage keywords (e.g., "homepage", "website") or falls back to the first candidate if no keywords match.
        
        Why:
        - To avoid overwriting existing metadata when a homepage is already known.
        - To infer a homepage from README content when metadata is missing, improving documentation completeness.
        
        Args:
            self: The AboutGenerator instance.
        
        Returns:
            The detected homepage URL as a string. Returns an empty string if no homepage can be determined (e.g., no README content, no URLs found, or no suitable candidates).
        """
        logger.info("Detecting homepage URL...")
        if self.metadata and self.metadata.homepage_url:
            logger.warning("Homepage already exists in metadata. Skipping generation.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SKIPPED,
                    target="about.homepage",
                    data={"reason": "already_exists"},
                )
            )
            return self.metadata.homepage_url

        if not self.readme_content:
            logger.warning("No README content found. Cannot detect homepage.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SKIPPED,
                    target="about.homepage",
                    data={"reason": "no_readme"},
                )
            )
            return ""

        urls = self._extract_readme_urls(self.readme_content)
        if not urls:
            logger.info("No URLs found in README")
            return ""

        candidates = self._analyze_urls(urls)
        logger.debug(f"Detected homepage: {candidates}")

        for url in candidates:
            if any(key in url.lower() for key in HOMEPAGE_KEYS):
                return url

        return candidates[0] if candidates else ""

    @staticmethod
    def _extract_readme_urls(readme_content: str) -> List[str]:
        """
        Extract all absolute URLs from README content.
        
        This method scans the provided README text to find all absolute URLs, which are useful for identifying external references, documentation links, or related resources mentioned in the README. Extracting these URLs helps in analyzing the project's external dependencies and linked content.
        
        Args:
            readme_content: The full text content of the README file from which URLs will be extracted.
        
        Returns:
            A list of unique absolute URLs found in the README content. Duplicates are removed.
        """
        logger.info("Extracting URLs from README.")
        url_pattern = r"(?:http|ftp|https):\/\/(?:[\w_-]+(?:(?:\.[\w_-]+)+))(?:[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])"
        urls = re.findall(url_pattern, readme_content)
        logger.debug(f"Extracted URLs from README: {urls}")
        return list(set(urls))

    def _analyze_urls(self, urls: List[str]) -> List[str]:
        """
        Generates LLM prompt for URL analysis and processes the response.
        
        This method constructs a prompt to analyze a list of project URLs using a language model.
        It logs the number of URLs being analyzed, sends the prompt via the model handler,
        and returns a cleaned list of URLs parsed from the model's response.
        
        Args:
            urls: A list of URL strings to be analyzed.
        
        Returns:
            A list of URL strings extracted and cleaned from the model's response.
            Returns an empty list if the model returns no response.
        
        Why:
            The method automates the analysis of project-related URLs (like documentation,
            homepage, or repository links) to identify or validate them using an LLM,
            supporting the overall goal of enhancing repository documentation.
        """
        logger.info(f"Analyzing {len(urls)} project URLs...")

        prompt = PromptBuilder.render(
            self.prompts.get("about_section.analyze_urls"), project_url=self.repo_url, urls=", ".join(urls)
        )
        response = self.model_handler.send_request(prompt)
        if not response:
            return []

        return [url.strip() for url in response.split(",")]
