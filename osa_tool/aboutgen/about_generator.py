import os
import re
import time
from typing import List, Optional

import requests

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

        self._content: Optional[dict] = None

    def generate_about_content(self) -> None:
        """
        Generates content for About section.
        """
        if self._content is not None:
            logger.warning(
                "About section content already generated. Skipping generation.")
            return
        self._content = {"description": self.generate_description(),
                         "homepage": self.detect_homepage(),
                         "topics": self.generate_topics()}

    def get_about_content(self) -> dict:
        """
        Returns the generated About section content.
        """
        if self._content is None:
            self.generate_about_content()
        return self._content

    def get_about_section_message(self) -> str:
        """
        Returns a formatted message for the GitHub About section.
        """
        logger.info("Started generating About section content.")
        if self._content is None:
            self.generate_about_content()

        about_section_content = (
            "You can add the following information to the `About` section of your GitHub repository:\n"
            f"- Description: {self._content['description']}\n"
            f"- Homepage: {self._content['homepage']}\n"
            f"- Topics: {', '.join(f'`{topic}`' for topic in self._content['topics'])}\n"
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
            topics=existing_topics,
            readme_content=self.readme_content,
        )

        try:
            response = self.model_handler.send_request(formatted_prompt)
            topics = [
                topic.strip().lower().replace(" ", "-")
                for topic in response.split(",")
                if topic.strip()
            ]
            logger.debug(f"Generated topics from LLM: {topics}")
            validated_topics = self._validate_github_topics(topics)
            return list(set([*existing_topics, *validated_topics]))
        except Exception as e:
            logger.error(f"Error generating topics: {e}")
            return []

    def _validate_github_topics(self, topics: List[str]) -> List[str]:
        """
        Validates topics against GitHub Topics API to ensure they exist.
        
        Args:
            topics (List[str]): List of potential topics to validate
            
        Returns:
            List[str]: List of validated topics that exist on GitHub
        """
        logger.info("Validating topics against GitHub Topics API...")
        min_repo = 5
        validated_topics = []

        for topic in topics:
            try:
                response = requests.get(
                    f"https://api.github.com/search/topics?q={topic}+repositories:>{min_repo}",
                    headers={"Accept": "application/vnd.github.v3+json"}
                )

                if response.status_code == 200:
                    data = response.json()
                    if (total := data.get("total_count", 0)) > 0:
                        if total == 1:
                            valid_topic = data.get("items")[0].get("name")
                            logger.debug(
                                f"Applied transformation for topic: '{topic} -> {valid_topic}'")
                        else:
                            valid_topic = topic
                        validated_topics.append(valid_topic)
                    else:
                        logger.debug(
                            f"Generated topic '{topic}' is not valid, skipping")
                elif response.status_code == 403:
                    logger.warning("Rate limit exceeded, waiting 60 seconds")
                    time.sleep(60)

                time.sleep(1)

            except Exception as e:
                logger.error(f"Error validating topic '{topic}': {e}")
                continue

        logger.info(
            f"Validated {len(validated_topics)} topics out of {len(topics)}")
        return validated_topics

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
        url_pattern = r'(?:http|ftp|https):\/\/(?:[\w_-]+(?:(?:\.[\w_-]+)+))(?:[\w.,@?^=%&:\/~+#-]*[\w@?^=%&\/~+#-])'
        urls = re.findall(url_pattern, readme_content)
        logger.debug(f"Extracted URLs from README: {urls}")
        return list(set(urls))

    def _analyze_urls(self, urls: List[str]) -> List[str]:
        """Generates LLM prompt for URL analysis"""
        logger.info(f"Analyzing {len(urls)} project URLs...")
        formatted_prompt = self.prompts.analyze_urls.format(
            project_url=self.repo_url,
            urls=", ".join(urls)
        )
        response = self.model_handler.send_request(formatted_prompt)
        if not response:
            return []

        return [url.strip() for url in response.split(",")]
