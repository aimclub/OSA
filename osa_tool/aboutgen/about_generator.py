from typing import Dict, List, Optional

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.utils import extract_readme_content, logger, parse_folder_name


class AboutGenerator:
    """Generates GitHub repository About section content."""

    def __init__(self, 
                 config_loader: ConfigLoader,
                 sourcerank: SourceRank):
        self.config = config_loader.config
        self.sourcerank = sourcerank
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = parse_folder_name(self.repo_url)

    def generate_about_section(self) -> Dict[str, any]:
        """Generate complete About section content."""
        return {
            "description": self._generate_description(),
            "homepage": self._detect_homepage(),
            "topics": self._generate_topics()
        }

    def _generate_description(self) -> str:
        """
        Generate repository description based on README content.
        If description already exists in metadata, return it.
        Otherwise, use LLM to generate a concise description.
        """
        if self.metadata and self.metadata.description:
            return self.metadata.description

        readme_content = extract_readme_content(self.base_path)
        if not readme_content:
            return ""

        prompt = (
            "Based on the following README content, generate a concise one-line description "
            "for the GitHub repository (max 150 characters):\n\n"
            f"{readme_content}\n\n"
            "Return only the description text without quotes or additional formatting."
        )

        try:
            description = self.model_handler.send_request(prompt)
            return description[:150]
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

    