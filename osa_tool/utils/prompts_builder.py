import os
from collections.abc import Iterable
from pathlib import Path

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
    def render(template: str, safe: bool = False, **kwargs) -> str:
        """
        Render template using Python's format(), unless safe=True.
        """
        try:
            if safe:
                return template
            return template.format(**kwargs)
        except KeyError as e:
            missing = e.args[0]
            raise PromptBuilderError(f"Missing argument for prompt rendering: '{missing}'")
        except Exception as e:
            raise PromptBuilderError(f"Failed to render prompt: {e}")


class PromptLoader:
    """
    Loads TOML prompt files from OSA's prompt directory plus optional overrides.

    Allows accessing prompts using keys like:
        "readme.translate"
        "readme.prompts.section_generate"
        "readme.system_messages.base"
    """

    def __init__(
        self,
        prompts_dir: str | os.PathLike[str] | None = None,
        override_dirs: Iterable[str | os.PathLike[str]] | None = None,
    ):
        self.prompts_dir = (
            Path(prompts_dir) if prompts_dir is not None else Path(osa_project_root()) / "config" / "prompts"
        )
        self.cache: dict[str, dict[str, str]] = {}
        self._load_all(self.prompts_dir)
        for override_dir in override_dirs or []:
            self._load_all(Path(override_dir), override=True)

    def _load_all(self, prompts_dir: str | os.PathLike[str] | None = None, *, override: bool = False):
        """Load all TOML prompt files (including nested directories) into memory."""
        root_dir = Path(prompts_dir) if prompts_dir is not None else self.prompts_dir
        if not root_dir.exists():
            label = "Prompt override directory" if override else "Prompts directory"
            raise PromptLoadError(f"{label} not found: {root_dir}")
        if not root_dir.is_dir():
            label = "Prompt override path" if override else "Prompts path"
            raise PromptLoadError(f"{label} is not a directory: {root_dir}")

        for root, _, files in os.walk(root_dir):
            for filename in files:
                if not filename.endswith(".toml"):
                    continue

                path = Path(root) / filename
                rel_path = path.relative_to(root_dir)
                # Example: "readme/system_messages.toml" -> "readme.system_messages"
                section_name = rel_path.with_suffix("").as_posix().replace("/", ".")

                try:
                    with path.open("rb") as f:
                        data = tomli.load(f)
                except Exception as e:
                    raise PromptLoadError(f"Failed to parse {rel_path}: {e}") from e

                if "prompts" not in data:
                    raise PromptLoadError(f"No [prompts] section in {rel_path}")

                prompts = data["prompts"]
                if override:
                    self.cache.setdefault(section_name, {}).update(prompts)
                else:
                    self.cache[section_name] = prompts

    def get(self, key: str) -> str:
        """
        Get a prompt by global key: "<section_path>.<prompt_name>".

        Examples:
            get("readme.translate")
            get("readme.prompts.section_generate")
            get("readme.system_messages.base")

        Raises:
            PromptLoadError: If section or key does not exist.
        """
        if "." not in key:
            raise PromptLoadError(
                f"Invalid prompt key '{key}'. Expected format: section.name (e.g. 'readme.translate')"
            )

        section, name = key.rsplit(".", 1)

        try:
            return self.cache[section][name]
        except KeyError:
            raise PromptLoadError(f"Prompt '{key}' not found in loaded prompts")
