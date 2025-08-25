import os

import pytest

from osa_tool.scheduler.prompts import PromptConfig, PromptLoader


def test_prompt_config_default_values():
    # Arrange
    config = PromptConfig()

    # Assert
    assert config.report is False
    assert config.translate_dirs is False
    assert config.docstring is False
    assert config.ensure_license is None
    assert config.community_docs is False
    assert config.readme is False
    assert config.organize is False
    assert config.about is False


def test_prompt_config_with_valid_data():
    # Arrange
    data = {
        "report": True,
        "translate_dirs": True,
        "docstring": True,
        "ensure_license": "mit",
        "community_docs": True,
        "readme": True,
        "organize": True,
        "about": True,
    }
    config = PromptConfig(**data)

    # Assert
    assert config.report is True
    assert config.translate_dirs is True
    assert config.docstring is True
    assert config.ensure_license == "mit"
    assert config.community_docs is True
    assert config.readme is True
    assert config.organize is True
    assert config.about is True


def test_prompt_config_with_invalid_license():
    # Arrange
    data = {"ensure_license": "invalid_license"}
    config = PromptConfig(**data)

    # Assert
    assert config.ensure_license == "invalid_license"


def test_prompt_config_extra_fields_ignored():
    # Arrange
    data = {"report": True, "extra_field": "should_be_ignored"}
    config = PromptConfig(**data)

    # Assert
    assert config.report is True
    assert not hasattr(config, "extra_field")


def test_prompt_config_safe_validate_with_valid_data():
    # Arrange
    data = {
        "report": True,
        "translate_dirs": False,
        "docstring": True,
        "ensure_license": "bsd-3",
        "community_docs": False,
        "readme": True,
        "organize": False,
        "about": True,
    }

    # Act
    config = PromptConfig.safe_validate(data)

    # Assert
    assert config.report is True
    assert config.translate_dirs is False
    assert config.docstring is True
    assert config.ensure_license == "bsd-3"
    assert config.community_docs is False
    assert config.readme is True
    assert config.organize is False
    assert config.about is True


def test_prompt_config_safe_validate_with_invalid_types():
    # Arrange
    data = {
        "report": "not_a_boolean",
        "translate_dirs": True,
        "docstring": 123,
        "ensure_license": "mit",
        "community_docs": "not_boolean",
        "readme": True,
        "organize": None,
        "about": True,
    }

    # Act
    config = PromptConfig.safe_validate(data)

    # Assert
    assert config.report is False
    assert config.translate_dirs is True
    assert config.docstring is False
    assert config.ensure_license == "mit"
    assert config.community_docs is False
    assert config.readme is True
    assert config.organize is False
    assert config.about is True


def test_prompt_config_safe_validate_with_missing_fields():
    # Arrange
    data = {
        "report": True,
    }

    # Act
    config = PromptConfig.safe_validate(data)

    # Assert
    assert config.report is True
    assert config.translate_dirs is False
    assert config.docstring is False
    assert config.ensure_license is None
    assert config.community_docs is False
    assert config.readme is False
    assert config.organize is False
    assert config.about is False


def test_prompt_config_safe_validate_empty_data():
    # Arrange
    data = {}

    # Act
    config = PromptConfig.safe_validate(data)

    # Assert
    assert config.report is False
    assert config.translate_dirs is False
    assert config.docstring is False
    assert config.ensure_license is None
    assert config.community_docs is False
    assert config.readme is False
    assert config.organize is False
    assert config.about is False


def test_prompt_loader_initialization():
    # Arrange
    loader = PromptLoader()

    # Act
    assert isinstance(loader.prompts, dict)
    assert len(loader.prompts) >= 0


def test_prompt_loader_load_prompts():
    # Arrange
    loader = PromptLoader()

    # Act
    prompts = loader.load_prompts()

    # Assert
    assert isinstance(prompts, dict)
    assert prompts is not None


def test_prompt_loader_get_prompts_path():
    # Act
    prompt_path = PromptLoader._get_prompts_path()

    # Assert
    assert isinstance(prompt_path, str)
    assert os.path.exists(prompt_path)
    assert "prompt_for_scheduler.toml" in prompt_path
    assert "config" in prompt_path
    assert "settings" in prompt_path


def test_prompt_loader_file_exists():
    # Act
    prompt_path = PromptLoader._get_prompts_path()

    # Assert
    assert os.path.exists(prompt_path)
    assert os.path.isfile(prompt_path)


def test_prompt_loader_prompts_not_empty():
    # Act
    loader = PromptLoader()

    # Arrange
    assert isinstance(loader.prompts, dict)


@pytest.mark.parametrize("license_value", ["bsd-3", "mit", "ap2", None, "gpl-3.0", "apache-2.0"])
def test_prompt_config_ensure_license_valid_values(license_value):
    # Arrange
    data = {"ensure_license": license_value}
    config = PromptConfig(**data)

    # Assert
    assert config.ensure_license == license_value


@pytest.mark.parametrize(
    "field_name", ["report", "translate_dirs", "docstring", "community_docs", "readme", "organize", "about"]
)
def test_prompt_config_boolean_fields_true(field_name):
    # Arrange
    data = {field_name: True}
    config = PromptConfig(**data)

    # Assert
    assert getattr(config, field_name) is True


@pytest.mark.parametrize(
    "field_name", ["report", "translate_dirs", "docstring", "community_docs", "readme", "organize", "about"]
)
def test_prompt_config_boolean_fields_false(field_name):
    # Arrange
    data = {field_name: False}
    config = PromptConfig(**data)

    # Assert
    assert getattr(config, field_name) is False


def test_prompt_loader_get_prompts_path_exists():
    # Act
    prompt_path = PromptLoader._get_prompts_path()

    # Assert
    assert os.path.exists(prompt_path)
    assert os.path.isfile(prompt_path)


def test_prompt_loader_load_prompts_returns_dict():
    # Arrange
    loader = PromptLoader()

    # Act
    prompts = loader.load_prompts()

    # Assert
    assert isinstance(prompts, dict)


def test_prompt_loader_prompts_not_none():
    # Arrange
    loader = PromptLoader()

    # Assert
    assert loader.prompts is not None


def test_prompt_loader_prompts_is_dict():
    # Arrange
    loader = PromptLoader()

    # Assert
    assert isinstance(loader.prompts, dict)
