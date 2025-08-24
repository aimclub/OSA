import pytest

from osa_tool.aboutgen.prompts_about_config import PromptAboutLoader, PromptConfig
from tests.utils.mocks.about_section_prompts import create_temp_toml_file, VALID_TOML_CONTENT, INVALID_TOML_CONTENT


def test_load_prompts_success(monkeypatch, tmp_path):
    # Arrange
    _ = create_temp_toml_file(tmp_path, VALID_TOML_CONTENT)

    monkeypatch.setattr("osa_tool.aboutgen.prompts_about_config.osa_project_root", lambda: str(tmp_path))
    # Act
    loader = PromptAboutLoader()

    # Assert
    assert isinstance(loader.prompts, PromptConfig)
    assert loader.prompts.description == "Description prompt"
    assert loader.prompts.topics == "Topics prompt"
    assert loader.prompts.analyze_urls == "Analyze URLs prompt"


def test_load_prompts_file_not_found(monkeypatch, tmp_path):
    # Arrange
    monkeypatch.setattr("osa_tool.aboutgen.prompts_about_config.osa_project_root", lambda: str(tmp_path))
    with pytest.raises(FileNotFoundError) as exc_info:
        _ = PromptAboutLoader()
    # Assert
    assert "prompts_about_section.toml" in str(exc_info.value)


def test_load_prompts_invalid_structure(monkeypatch, tmp_path):
    # Arrange
    _ = create_temp_toml_file(tmp_path, INVALID_TOML_CONTENT)
    monkeypatch.setattr("osa_tool.aboutgen.prompts_about_config.osa_project_root", lambda: str(tmp_path))
    with pytest.raises(Exception) as exc_info:
        _ = PromptAboutLoader()

    # Assert
    assert "field required" in str(exc_info.value) or "missing" in str(exc_info.value).lower()
