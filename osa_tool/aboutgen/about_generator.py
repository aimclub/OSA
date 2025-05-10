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

    def _generate_topics(self) -> List[str]:
        """
        Get repository topics from metadata if they exist,
        otherwise generate them using LLM based on README content.
        Returns up to 5 most relevant topics.
        """
        if self.metadata and self.metadata.topics:
            return self.metadata.topics

        readme_content = extract_readme_content(self.base_path)
        if not readme_content:
            return []

        prompt = (
            "Based on the following README content, generate up to 5 relevant GitHub topics.\n"
            "Topics should be lowercase, use hyphens instead of spaces, and be relevant to:\n"
            "- Main programming language\n"
            "- Framework or technology\n"
            "- Problem domain\n"
            "- Type of project (e.g., library, tool, framework)\n\n"
            f"README content:\n{readme_content}\n\n"
            "Return only topics as a comma-separated list, for example:\n"
            "code analysis, code improvement, llm, open source, scientific software"
        )

        try:
            response = self.model_handler.send_request(prompt)
            topics = [
                topic.strip().lower().replace(" ", "-")
                for topic in response.split(",")
                if topic.strip()
            ]
            logger.debug(f"Generated topics from LLM: {topics}")
            return topics[:5]
        except Exception as e:
            logger.error(f"Error generating topics: {e}")
            return []

    def _detect_homepage(self) -> Optional[str]:
        """Detect and validate homepage URL."""
        pass

    