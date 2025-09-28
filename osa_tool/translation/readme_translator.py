import asyncio
import json
import os

from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandlerFactory, ModelHandler
from osa_tool.readmegen.postprocessor.response_cleaner import process_text
from osa_tool.readmegen.prompts.prompts_builder import PromptBuilder
from osa_tool.readmegen.utils import read_file, save_sections, remove_extra_blank_lines
from osa_tool.utils import parse_folder_name, logger


class ReadmeTranslator:
    def __init__(self, config_loader: ConfigLoader, languages: list[str]):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.rate_limit = self.config.llm.rate_limit
        self.languages = languages
        self.repo_url = self.config.git.repository
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

    async def translate_readme_request_async(
        self, readme_content: str, target_language: str, semaphore: asyncio.Semaphore
    ) -> dict:
        """Asynchronous request to translate README content via LLM."""
        prompt = PromptBuilder(self.config_loader).get_prompt_translate_readme(readme_content, target_language)
        async with semaphore:
            response = await self.model_handler.async_request(prompt)
            response = process_text(response)
        try:
            result = json.loads(response)
        except json.JSONDecodeError:
            logger.warning(f"LLM response for '{target_language}' is not valid JSON, applying fallback")
            result = {
                "content": response.strip(),
                "suffix": target_language[:2].lower(),
            }
        return result

    async def translate_readme_async(self) -> None:
        """
        Asynchronously translate the main README into all target languages.
        """
        readme_content = self.get_main_readme_file()
        if not readme_content:
            logger.warning("No README content found, skipping translation")
            return

        semaphore = asyncio.Semaphore(self.rate_limit)

        async def translate_and_save(lang: str):
            translation = await self.translate_readme_request_async(readme_content, lang, semaphore)
            self.save_translated_readme(translation)

        await asyncio.gather(*(translate_and_save(lang) for lang in self.languages))

    def save_translated_readme(self, translation: dict) -> None:
        """
        Save a single translated README to a file.

        Args:
            translation (dict): Dictionary with keys:
                - "content": translated README text
                - "suffix": language code
        """
        suffix = translation.get("suffix", "unknown")
        content = translation.get("content", "")

        if not content:
            logger.warning(f"Translation for '{suffix}' is empty, skipping save.")
            return

        filename = f"README_{suffix}.md"
        file_path = os.path.join(self.base_path, filename)

        save_sections(content, file_path)
        remove_extra_blank_lines(file_path)
        logger.info(f"Saved translated README: {file_path}")

    def get_main_readme_file(self) -> str:
        """Return the content of the main README.md in the repository root, or empty string if not found."""
        readme_path = os.path.join(self.base_path, "README.md")
        return read_file(readme_path)

    def translate_readme(self) -> None:
        """Synchronous wrapper around async translation."""
        asyncio.run(self.translate_readme_async())
