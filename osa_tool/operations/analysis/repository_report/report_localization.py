import os

import tomli

from osa_tool.operations.analysis.repository_report.response_validation import YesNoPartial
from osa_tool.utils.utils import osa_project_root

DEFAULT_LANGUAGE = "English"


class LocaleLoadError(Exception):
    """Raised when loading locale files from config/locales/ fails."""


def _load_translations() -> dict[str, dict[str, str]]:
    """
    Loads all locale TOML files inside: osa_tool/config/locales/

    Each file must declare a top-level `language` key and a [translations] table, e.g.:

        language = "English"

        [translations]
        report_header = "Repository Analysis Report"

    Adding support for a new language is just a matter of dropping a new file here -
    no code changes required.
    """
    locales_dir = os.path.join(osa_project_root(), "config", "locales")
    if not os.path.exists(locales_dir):
        raise LocaleLoadError(f"Locales directory not found: {locales_dir}")

    translations: dict[str, dict[str, str]] = {}
    for filename in sorted(os.listdir(locales_dir)):
        if not filename.endswith(".toml"):
            continue

        path = os.path.join(locales_dir, filename)
        try:
            with open(path, "rb") as f:
                data = tomli.load(f)
        except Exception as e:
            raise LocaleLoadError(f"Failed to parse {filename}: {e}") from e

        language = data.get("language")
        if not language:
            raise LocaleLoadError(f"Missing top-level 'language' key in {filename}")
        if "translations" not in data:
            raise LocaleLoadError(f"No [translations] section in {filename}")

        translations[language] = data["translations"]

    if DEFAULT_LANGUAGE not in translations:
        raise LocaleLoadError(f"Locale files must include a '{DEFAULT_LANGUAGE}' locale as the fallback base")

    return translations


TRANSLATIONS = _load_translations()


class ReportTranslationManager:
    def __init__(self, target_language: str):
        self.target_language = target_language if target_language in TRANSLATIONS else DEFAULT_LANGUAGE
        self._base = TRANSLATIONS[DEFAULT_LANGUAGE]
        self._translations = TRANSLATIONS[self.target_language]

    def get(self, key: str) -> str | None:
        # Fall back to the base (English) locale if the target one is missing a key,
        # e.g. because it hasn't caught up with recently added keys yet.
        return self._translations.get(key, self._base.get(key))

    def yes_no_partial(self, key: YesNoPartial) -> str | None:
        if key == YesNoPartial.YES:
            return self.get("yes")
        elif key == YesNoPartial.NO:
            return self.get("no")
        elif key == YesNoPartial.PARTIAL:
            return self.get("partial")
        return self.get("unknown")
