import pytest

from osa_tool.operations.analysis.repository_report.report_localization import (
    DEFAULT_LANGUAGE,
    TRANSLATIONS,
    ReportTranslationManager,
)
from osa_tool.operations.analysis.repository_report.response_validation import YesNoPartial


def test_all_locales_are_loaded():
    # Assert
    assert DEFAULT_LANGUAGE in TRANSLATIONS
    assert "Russian" in TRANSLATIONS


@pytest.mark.parametrize("language", list(TRANSLATIONS.keys()))
def test_locale_has_no_missing_keys_relative_to_default(language):
    # Arrange
    base_keys = set(TRANSLATIONS[DEFAULT_LANGUAGE].keys())

    # Assert
    missing = base_keys - set(TRANSLATIONS[language].keys())
    assert not missing, f"Locale '{language}' is missing keys present in '{DEFAULT_LANGUAGE}': {missing}"


def test_translation_manager_falls_back_to_default_language_for_unknown_language():
    # Act
    manager = ReportTranslationManager("Klingon")

    # Assert
    assert manager.target_language == DEFAULT_LANGUAGE
    assert manager.get("report_header") == TRANSLATIONS[DEFAULT_LANGUAGE]["report_header"]


def test_translation_manager_returns_requested_language_value():
    # Act
    manager = ReportTranslationManager("Russian")

    # Assert
    assert manager.get("report_header") == TRANSLATIONS["Russian"]["report_header"]


def test_translation_manager_yes_no_partial():
    # Act
    manager = ReportTranslationManager("English")

    # Assert
    assert manager.yes_no_partial(YesNoPartial.YES) == "Yes"
    assert manager.yes_no_partial(YesNoPartial.NO) == "No"
    assert manager.yes_no_partial(YesNoPartial.PARTIAL) == "Partial"
    assert manager.yes_no_partial(YesNoPartial.UNKNOWN) == "Unknown"
