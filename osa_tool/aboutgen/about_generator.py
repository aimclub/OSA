import os
import re
from typing import Dict, List, Optional

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.utils import extract_readme_content, logger, parse_folder_name


class AboutGenerator:
    """Generates GitHub repository About section content."""

    def __init__(self, 
                 config_loader: ConfigLoader):
        self.config = config_loader.config
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = os.path.join(
            os.getcwd(), parse_folder_name(self.repo_url))
        self.readme_content = extract_readme_content(self.base_path)

    def generate_about_section(self) -> Dict[str, any]:
        """
        Generates complete About section content that consists of description,
        homepage, and topics.
        """
        logger.info("Started generating About section content.")
        about_section_data = {
            "description": self.generate_description(),
            "homepage": self.detect_homepage(),
            "topics": self.generate_topics()
        }
        logger.info("Finished generating About section content.")
        return about_section_data

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

        prompt = (
            "Create a technical, concise GitHub repository description (120 chars) from README content below.\n"
            "Focus on:\n"
            "- Core functionality/automation provided\n"
            "- Key technical differentiation\n"
            "- Problem domain/specialization\n"
            "- Primary architectural pattern\n"
            "Avoid:\n"
            "- Marketing language ('easy', 'powerful')\n"
            "- Generic verbs('helps with', 'manages')\n"
            "- Repository type mentions unless novel\n\n"
            "Format: Third person technical voice. Example outputs:\n"
            "1. 'Dynamic DNS updater with Docker support and Let's Encrypt integration'\n"
            "2. 'Distributed graph processing engine using actor model parallelism'\n\n"
            f"README content:\n{self.readme_content}\n\n"
            "Return only the final description text with no commentary."
        )

        try:
            description = self.model_handler.send_request(prompt)
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
        if self.metadata and self.metadata.topics:
            if amount > 20:
                logger.critical("Maximum amount of topics is 20.")
                return self.metadata.topics
            if len(self.metadata.topics) >= amount:
                logger.warning(
                    f"{amount} topics already exist in the metadata. Skipping generation.")
                return self.metadata.topics

        if not self.readme_content:
            logger.error(
                "No README content found. Cannot generate topics.")
            return []

        prompt = (
            "Analyze the README content and already existing topics below"
            f"to generate up to {amount} specific, technical GitHub topics focusing on:\n"
            "1. Specialized libraries/packages used (beyond base framework)\n"
            "2. Core algorithms/technical approaches\n"
            "3. Specific problem sub-domains\n"
            "4. Implementation patterns/architectural styles\n"
            "5. Key technical differentiators\n\n"
            "Avoid generic terms like programming languages or frameworks unless they are novel implementations.\n"
            "Do not change the existing topics.\n"
            "Format: lowercase, hyphens, technical terms only, use 50 characters per topic or less. Example:\n"
            "computer-vision, graph-algorithms, genetic-algorithm, distributed-systems, gpu-acceleration\n\n"
            f"README content:\n{self.readme_content}\n\n"
            f"Existing topics: {', '.join(self.metadata.topics)}\n\n"
            "Return only topics as a comma-separated list without explanations."
        )

        try:
            response = self.model_handler.send_request(prompt)
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

    def _detect_homepage(self) -> Optional[str]:
        """Detect and validate homepage URL."""
        pass

    