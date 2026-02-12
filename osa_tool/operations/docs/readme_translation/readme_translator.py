import asyncio
import os
import shutil

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.llm.llm import ModelHandlerFactory, ModelHandler
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.docs.readme_generation.utils import read_file, save_sections, remove_extra_blank_lines
from osa_tool.scheduler.plan import Plan
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import parse_folder_name


class ReadmeTranslator:
    """
    Translates README.md into multiple languages and stores translated files
    in the repository root (README_xx.md) and optionally sets a default one.
    """

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata, plan: Plan):
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("readme")
        self.prompts = self.config_manager.get_prompts()
        self.rate_limit = self.model_settings.rate_limit
        self.languages = plan.get("translate_readme")
        self.metadata = metadata
        self.repo_url = self.config_manager.get_git_settings().repository
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.plan = plan

        self.events: list[OperationEvent] = []

    def translate_readme(self) -> dict:
        """
        Synchronous wrapper around async translation.

        Returns:
            dict with:
                - result: summary of translations
                - events: list of OperationEvent
        """
        asyncio.run(self._translate_readme_async())

        return {
            "result": {
                "languages": self.languages,
                "translated": [e.data.get("language") for e in self.events if e.kind == EventKind.WRITTEN],
            },
            "events": self.events,
        }

    async def _translate_readme_async(self) -> None:
        """
        Asynchronously translate the main README into all target languages.
        """
        readme_content = self._get_main_readme_file()
        if not readme_content:
            logger.warning("No README content found, skipping translation")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SKIPPED,
                    target="README.md",
                    data={"reason": "not_found"},
                )
            )
            return

        semaphore = asyncio.Semaphore(self.rate_limit)

        results: dict[str, dict] = {}

        async def translate_and_save(lang: str):
            translation = await self._translate_readme_request_async(readme_content, lang, semaphore)
            self._save_translated_readme(translation)
            results[lang] = translation

        await asyncio.gather(*(translate_and_save(lang) for lang in self.languages))

        if self.languages:
            first_lang = self.languages[0]
            if first_lang in results:
                self._set_default_translated_readme(results[first_lang])
            else:
                logger.warning(f"No translation found for first language '{first_lang}'")

    async def _translate_readme_request_async(
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

    def _save_translated_readme(self, translation: dict) -> None:
        """
        Save a single translated README to a file.

        Args:
            translation (dict): Dictionary with keys:
                - "content": translated README text
                - "suffix": language code
        """
        suffix = translation.get("suffix", "unknown")
        language = translation.get("target_language", "unknown")
        content = translation.get("content", "")

        if not content:
            logger.warning(f"Translation for '{suffix}' is empty, skipping save.")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SKIPPED,
                    target="README.md",
                    data={"language": language, "reason": "empty_translation"},
                )
            )
            return

        filename = f"README_{suffix}.md"
        file_path = os.path.join(self.base_path, filename)

        save_sections(content, file_path)
        remove_extra_blank_lines(file_path)
        logger.info(f"Saved translated README: {file_path}")
        self.events.append(
            OperationEvent(
                kind=EventKind.WRITTEN,
                target=filename,
                data={"language": language, "path": file_path},
            )
        )

    def _set_default_translated_readme(self, translation: dict) -> None:
        """
        Create a .github/README.md symlink (or copy fallback)
        pointing to the first translated README.
        """
        suffix = translation.get("suffix")
        language = translation.get("target_language", "unknown")
        source_path = os.path.join(self.base_path, f"README_{suffix}.md")
        github_dir = os.path.join(self.base_path, ".github")
        target_path = os.path.join(github_dir, "README.md")

        if not suffix:
            logger.warning("No suffix for first translated README, skipping default setup.")
            return

        if not os.path.exists(source_path):
            logger.warning(f"Translated README not found at {source_path}, skipping setup.")
            return

        os.makedirs(github_dir, exist_ok=True)

        try:
            if os.path.exists(target_path):
                os.remove(target_path)

            shutil.copyfile(source_path, target_path)
            logger.info(f"Copied file: {target_path}")
            self.events.append(
                OperationEvent(
                    kind=EventKind.SET,
                    target=".github/README.md",
                    data={"language": language},
                )
            )
        except (OSError, NotImplementedError) as e:
            logger.error("Failed to set default README: %s", e)
            self.events.append(
                OperationEvent(
                    kind=EventKind.FAILED,
                    target=".github/README.md",
                    data={"error": str(e)},
                )
            )

    def _get_main_readme_file(self) -> str:
        """Return the content of the main README.md in the repository root, or empty string if not found."""
        readme_path = os.path.join(self.base_path, "README.md")
        return read_file(readme_path)
