import asyncio
import os
import shutil

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.llm.llm import ModelHandlerFactory, ModelHandler
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.docs.readme_generation.utils import read_file, save_sections, remove_extra_blank_lines
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import parse_folder_name


class ReadmeTranslator:
    """
    Translates README.md into multiple languages and stores translated files
        in the repository root (README_xx.md) and optionally sets a default one.
    """


    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata, languages: list[str]):
        """
        Initializes the ReadmeTranslator instance with configuration, repository metadata, and language information.
        
        Args:
            config_manager: Configuration manager providing model settings, prompts, and git settings.
            metadata: Metadata about the repository.
            languages: List of programming languages present in the repository.
        
        Initializes the following class fields:
            config_manager (ConfigManager): Configuration manager instance.
            model_settings (ModelSettings): Model settings for the 'readme' task type, retrieved from the configuration manager.
            prompts (PromptLoader): Loader for prompt templates, retrieved from the configuration manager.
            rate_limit: Rate limit from the model settings, used to control request frequency to the language model.
            languages (list[str]): List of programming languages.
            metadata (RepositoryMetadata): Repository metadata.
            repo_url: URL of the Git repository, obtained from the git settings in the configuration manager.
            model_handler (ModelHandler): Model handler built from the model settings, used to interact with the language model.
            base_path: Absolute path to the directory where the repository will be cloned, derived by joining the current working directory with a folder name parsed from the repository URL.
            events (list[OperationEvent]): List to store operation events, initially empty.
        
        Why:
            The method sets up all necessary components for the ReadmeTranslator to operate, including configuration, model interaction, and repository context. It prepares the model handler for generating or translating README content and establishes the local directory path where the repository will be cloned for processing.
        """
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("readme")
        self.prompts = self.config_manager.get_prompts()
        self.rate_limit = self.model_settings.rate_limit
        self.languages = languages
        self.metadata = metadata
        self.repo_url = self.config_manager.get_git_settings().repository
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))

        self.events: list[OperationEvent] = []

    def translate_readme(self) -> dict:
        """
        Synchronous wrapper around the asynchronous translation workflow.
        
        This method provides a synchronous entry point for translating the main README into all target languages. It runs the underlying async translation process (`_translate_readme_async`) and returns a structured summary of the results and events.
        
        Why:
            It allows synchronous callers to invoke the translation without managing an asyncio event loop themselves. The method ensures the async operation completes and returns a consistent result format.
        
        Returns:
            dict: A dictionary containing:
                - result: A summary of the translations, including:
                    - languages: The list of target languages configured for translation.
                    - translated: A list of language codes for which translations were successfully written.
                - events: The complete list of OperationEvent objects emitted during the translation process.
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
        
        This method coordinates the translation workflow: it retrieves the main README content,
        then concurrently translates it into each target language using a rate‑limited semaphore.
        Each successful translation is saved to a separate file. If no README content is found,
        the operation is skipped and a warning is logged. After all translations are complete,
        the first language’s translation is set as the default README in the `.github` directory
        to provide a standardized entry point for GitHub’s interface.
        
        Args:
            self: The instance of the ReadmeTranslator class.
        
        Returns:
            None
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
        """
        Asynchronous request to translate README content via LLM.
        
        This method constructs a prompt for translation, sends it to the LLM asynchronously
        with concurrency control via a semaphore, and processes the response into a
        structured dictionary. It ensures the result contains required fields for downstream use.
        
        Args:
            readme_content: The original README text to be translated.
            target_language: The language into which the README should be translated.
            semaphore: An asyncio.Semaphore used to limit concurrent LLM requests.
        
        Returns:
            A dictionary containing the translation result with the following keys:
                - 'content': The translated README text. If the LLM response does not
                  provide this, it defaults to a cleaned version of the raw response.
                - 'suffix': A two‑letter language code derived from `target_language`.
                - 'target_language': The original `target_language` argument.
                - Any additional keys parsed from the LLM's JSON response.
        
        Why:
            The semaphore is used to prevent overwhelming the LLM service with too many
            simultaneous requests, which could lead to rate‑limiting or performance issues.
            Default values for 'content' and 'suffix' are set to guarantee the dictionary
            always has the structure expected by the rest of the translation pipeline.
        """
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

    def _save_translated_readme(self, translation: dict) -> None:
        """
        Save a single translated README to a file.
        
        WHY: This method handles the final step of persisting a translated README to disk, ensuring the content is non‑empty, properly formatted, and logged for tracking. It also records the operation outcome (written or skipped) in the event list for later reporting.
        
        Args:
            translation (dict): Dictionary containing the translation result. Expected keys are:
                - "content": the translated README text as a string.
                - "suffix": language code (e.g., "es", "fr") used in the output filename.
                - "target_language": full language name for logging and events (optional; defaults to "unknown").
        
        If the content is empty, a warning is logged, an event is recorded as skipped, and no file is saved. Otherwise, the content is written to a Markdown file named `README_{suffix}.md` in the instance's base path, extra blank lines are removed for clean formatting, and a written event is appended.
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
        Create a .github/README.md symlink (or copy fallback) pointing to the first translated README.
        
        This method ensures that a default README is available in the `.github` directory by copying the first successfully translated README file. It is used to provide a standardized, language-specific README for GitHub's interface when multiple translations exist.
        
        Args:
            translation: A dictionary containing translation metadata, which must include a 'suffix' key (the language suffix for the translated file) and may include a 'target_language' key (the human-readable language name).
        
        Behavior:
        - If the translation dictionary lacks a 'suffix', logs a warning and exits.
        - If the translated source file does not exist, logs a warning and exits.
        - Creates the `.github` directory if it does not exist.
        - Removes any existing `.github/README.md` file before copying the new one.
        - On success, logs the copy operation and records a SET event with the target language.
        - On failure (e.g., permission errors, unsupported symlink operations), logs an error and records a FAILED event with the error details.
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
        """
        Return the content of the main README.md file located in the repository root, or an empty string if the file is not found or cannot be read.
        
        The method constructs the full path to README.md by joining the repository's base path with the filename. It then delegates reading to a helper function that handles file reading, decoding, and error cases—returning an empty string if the file is missing, unreadable, or an error occurs. This ensures the method safely provides README content when available without raising exceptions.
        
        Args:
            self: The instance of the ReadmeTranslator class.
        
        Returns:
            The content of README.md as a string, or an empty string if the file cannot be read.
        """
        readme_path = os.path.join(self.base_path, "README.md")
        return read_file(readme_path)
