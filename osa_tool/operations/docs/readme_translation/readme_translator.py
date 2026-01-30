import asyncio
import os
import shutil
from typing import List

from pydantic import BaseModel

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandlerFactory, ModelHandler
from osa_tool.operations.docs.readme_generation.utils import read_file, save_sections, remove_extra_blank_lines
from osa_tool.operations.registry import Operation, OperationRegistry
from osa_tool.scheduler.plan import Plan
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import parse_folder_name


class ReadmeTranslator:
    def __init__(self, config_loader: ConfigLoader, metadata: RepositoryMetadata, plan: Plan):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.prompts = self.config.prompts
        self.rate_limit = self.config.llm.rate_limit
        self.languages = plan.get("translate_readme")
        self.metadata = metadata
        self.repo_url = self.config.git.repository
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.plan = plan

    async def translate_readme_request_async(
        self, readme_content: str, target_language: str, semaphore: asyncio.Semaphore
    ) -> dict:
        """Asynchronous request to translate README content via LLM."""
        prompt = PromptBuilder.render(
            self.prompts.get("readme.translate"),
            target_language=target_language,
            readme_content=readme_content,
        )

        async with semaphore:
            parsed = await self.model_handler.async_send_and_parse(
                prompt=prompt,
                parser=lambda raw: JsonProcessor.parse(raw, expected_type=dict),
            )
        # Ensure required fields after validation
        parsed.setdefault("content", parsed.get("raw", "").strip())
        parsed.setdefault("suffix", target_language[:2].lower())
        parsed["target_language"] = target_language

        return parsed

    async def translate_readme_async(self) -> None:
        """
        Asynchronously translate the main README into all target languages.
        """
        self.plan.mark_started("translate_readme")
        readme_content = self.get_main_readme_file()
        if not readme_content:
            logger.warning("No README content found, skipping translation")
            self.plan.mark_failed("translate_readme")
            return

        semaphore = asyncio.Semaphore(self.rate_limit)

        results = {}

        async def translate_and_save(lang: str):
            try:
                translation = await self.translate_readme_request_async(readme_content, lang, semaphore)
                self.save_translated_readme(translation)
                results[lang] = translation
            except ConnectionError:
                logger.warning(f"Connection error for language '{lang}'")

        await asyncio.gather(*(translate_and_save(lang) for lang in self.languages))

        if not results:
            self.plan.mark_failed("translate_readme")
            return

        if self.languages:
            first_lang = self.languages[0]
            if first_lang in results:
                self.set_default_translated_readme(results[first_lang])
            else:
                logger.warning(f"No translation found for first language '{first_lang}'")
        self.plan.mark_done("translate_readme")

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

    def set_default_translated_readme(self, translation: dict) -> None:
        """
        Create a .github/README.md symlink (or copy fallback)
        pointing to the first translated README.
        """
        suffix = translation.get("suffix")
        if not suffix:
            logger.warning("No suffix for first translated README, skipping default setup.")
            return

        source_path = os.path.join(self.base_path, f"README_{suffix}.md")
        if not os.path.exists(source_path):
            logger.warning(f"Translated README not found at {source_path}, skipping setup.")
            return

        github_dir = os.path.join(self.base_path, ".github")
        os.makedirs(github_dir, exist_ok=True)

        target_path = os.path.join(github_dir, "README.md")

        try:
            if os.path.exists(target_path):
                os.remove(target_path)

            shutil.copyfile(source_path, target_path)
            logger.info(f"Copied file: {target_path}")
        except (OSError, NotImplementedError) as e:
            logger.error(f"Error while copying file: {e}")

    def get_main_readme_file(self) -> str:
        """Return the content of the main README.md in the repository root, or empty string if not found."""
        readme_path = os.path.join(self.base_path, "README.md")
        return read_file(readme_path)

    def translate_readme(self) -> None:
        """Synchronous wrapper around async translation."""
        asyncio.run(self.translate_readme_async())


class TranslateReadmeArgs(BaseModel):
    languages: List[str]


class TranslateReadmeOperation(Operation):
    name = "translate_readme"
    description = "Translate README.md into another language"

    supported_intents = ["new_task", "feedback"]
    supported_scopes = ["full_repo", "docs"]
    priority = 75

    args_schema = TranslateReadmeArgs
    args_policy = "ask_if_missing"
    prompt_for_args = (
        "For operation 'translate_readme' provide a list of languages " "(e.g., {'languages': ['Russian', 'Swedish']})."
    )

    executor = ReadmeTranslator
    executor_method = "translate_readme"
    executor_dependencies = ["config_loader", "metadata"]


OperationRegistry.register(TranslateReadmeOperation())
