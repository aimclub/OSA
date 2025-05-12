import os
import re
from typing import List, Optional

from osa_tool.aboutgen.prompts_about_config import PromptAboutLoader
from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.utils import extract_readme_content, logger, parse_folder_name

HOMEPAGE_KEYS = ["documentation", "doc", "docs", "about",
                 "homepage", "wiki", "gh-pages", "readthedocs", "netlify", "github.io"]

class AboutGenerator:
    """Generates GitHub repository About section content."""

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = os.path.join(
            os.getcwd(), parse_folder_name(self.repo_url))
        self.readme_content = extract_readme_content(self.base_path)
        self.prompts = PromptAboutLoader().prompts

    def generate_about_section(self) -> str:
        """
        Generates complete About section content that consists of description,
        homepage, and topics.
        """
        logger.info("Started generating About section content.")
        about_section_content = (
            "You can add the following information to the `About` section of your GitHub repository:\n"
            f"- Description: {self.generate_description()}\n"
            f"- Homepage: {self.detect_homepage()}\n"
            f"- Topics: {', '.join(self.generate_topics())}\n"
            "\nPlease review and add them to your repository.\n"
        )
        logger.debug(
            f"Generated About section content: {about_section_content}")
        logger.info("Finished generating About section content.")
        return about_section_content

    def generate_description(self) -> str:
        """
        Generates a repository description based on README content.

        Returns:
            str: A repository description (up to 150 characters) or an empty string
                 if README content is unavailable.
        """
        logger.info("Generating repository description...")
        if self.metadata and self.metadata.description:
            logger.warning(
                "Description already exists in metadata. Skipping generation.")
            return self.metadata.description

        if not self.readme_content:
            logger.warning(
                "No README content found. Cannot generate description.")
            return ""

        formatted_prompt = self.prompts.description.format(
            readme_content=self.readme_content)

        try:
            description = self.model_handler.send_request(formatted_prompt)
            logger.debug(f"Generated description: {description}")
            return description[:350]
        except Exception as e:
            logger.error(f"Error generating description: {e}")
            return ""

    def generate_topics(self, amount: int = 7) -> List[str]:
        """
        Generates GitHub repository topics based on README content.

        Args:
            amount (int): Maximum number of topics to return (default 7, max 20).

        Returns:
            List[str]: A list of up to `amount` topics, or an empty list if none can be generated.
        """
        logger.info(f"Generating up to {amount} topics...")
        existing_topics = []
        if self.metadata and hasattr(self.metadata, 'topics'):
            existing_topics = self.metadata.topics
            if amount > 20:
                logger.critical("Maximum amount of topics is 20.")
                return existing_topics
            if len(existing_topics) >= amount:
                logger.warning(
                    f"{amount} topics already exist in the metadata. Skipping generation.")
                return existing_topics

        formatted_prompt = self.prompts.topics.format(
            amount=amount,
            readme_content=self.readme_content,
            topics=", ".join(existing_topics)
        )

        try:
            response = self.model_handler.send_request(formatted_prompt)
            topics = [
                topic.strip().lower().replace(" ", "-")
                for topic in response.split(",")
                if topic.strip()
            ]
            logger.debug(f"Generated topics from LLM: {topics}")
            return topics[:amount]
        except Exception as e:
            logger.error(f"Error generating topics: {e}")
            return []

    def detect_homepage(self) -> Optional[str]:
        """
        Detects the homepage URL for a project.

        Returns:
            Optional[str]: The detected homepage URL, an empty string if none is found.
        """
        logger.info("Detecting homepage URL...")
        if self.metadata and self.metadata.homepage_url:
            logger.warning(
                "Homepage already exists in metadata. Skipping generation.")
            return self.metadata.homepage_url

        if not self.readme_content:
            logger.warning(
                "No README content found. Cannot detect homepage.")
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

    def _extract_readme_urls(self, readme_content: str) -> List[str]:
        """Extract all absolute URLs from README content"""
        logger.info("Extracting URLs from README.")
        url_pattern = r'https?:\/\/.*'
        urls = re.findall(url_pattern, readme_content)
        logger.debug(f"Extracted URLs from README: {urls}")
        return list(set(urls))

    def _analyze_urls(self, urls: List[str]) -> List[str]:
        """Generates LLM prompt for URL analysis"""
        logger.info(f"Analyzing project URLs...")
        formatted_prompt = self.prompts.analyze_urls.format(
            urls=", ".join(urls)
        )
        response = self.model_handler.send_request(formatted_prompt)
        if not response:
            return []

        return [url.strip() for url in response.split(",")]
