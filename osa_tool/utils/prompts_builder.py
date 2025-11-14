import os

import tomli

from osa_tool.utils.utils import osa_project_root


class PromptBuilderError(Exception):
    """Base exception for PromptBuilder errors."""


class PromptLoadError(PromptBuilderError):
    """Raised when loading prompts from a file fails."""


class PromptFormatError(PromptBuilderError):
    """Raised when formatting the prompt with arguments fails."""


class PromptBuilder:
    @staticmethod
    def render(template: str, **kwargs) -> str:
        """
        Render template using Python's format().
        Raises PromptBuilderError if any placeholder is missing.
        """
        try:
            return template.format(**kwargs)
        except KeyError as e:
            missing = e.args[0]
            raise PromptBuilderError(f"Missing argument for prompt rendering: '{missing}'")
        except Exception as e:
            raise PromptBuilderError(f"Failed to render prompt: {e}")


class PromptLoader:
    """
    Loads all prompt TOML files inside: osa_tool/config/prompts/

    Allows accessing prompts using keys like:
        "readme.preanalysis"
        "readme_article.file_summary"
    """

    def __init__(self):
        self.prompts_dir = os.path.join(osa_project_root(), "config", "prompts")
        self.cache: dict[str, dict[str, str]] = {}
        self._load_all()

    def _load_all(self):
        """Load all TOML prompt files into memory."""
        if not os.path.exists(self.prompts_dir):
            raise PromptLoadError(f"Prompts directory not found: {self.prompts_dir}")

        for filename in os.listdir(self.prompts_dir):
            if not filename.endswith(".toml"):
                continue

            path = os.path.join(self.prompts_dir, filename)
            section_name = filename[:-5]  # strip ".toml"

            try:
                with open(path, "rb") as f:
                    data = tomli.load(f)
            except Exception as e:
                raise PromptLoadError(f"Failed to parse {filename}: {e}") from e

            if "prompts" not in data:
                raise PromptLoadError(f"No [prompts] section in {filename}")

            self.cache[section_name] = data["prompts"]

    def get(self, key: str) -> str:
        """
        Get a prompt by global key: "section.prompt_name".

        Example:
            get("readme.preanalysis")
            get("article.main_prompt")

        Raises:
            PromptLoadError: If section or key does not exist.
        """
        if "." not in key:
            raise PromptLoadError(
                f"Invalid prompt key '{key}'. Expected format: section.name (e.g. 'readme.preanalysis')"
            )

        section, name = key.split(".", 1)

        try:
            return self.cache[section][name]
        except KeyError:
            raise PromptLoadError(f"Prompt '{key}' not found in loaded prompts")
