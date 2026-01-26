import asyncio
import json
import os
from unittest.mock import patch, AsyncMock

import pytest

import osa_tool.operations.docs.readme_translation.readme_translator as rt


@pytest.fixture
def translator(tmp_path, mock_config_manager, mock_repository_metadata):
    t = rt.ReadmeTranslator(mock_config_manager, mock_repository_metadata, ["fr", "de"])
    t.base_path = tmp_path
    return t


def test_get_main_readme_file_found(translator, tmp_path):
    # Arrange
    readme = tmp_path / "README.md"
    readme.write_text("hello readme")

    # Assert
    assert translator.get_main_readme_file() == "hello readme"


def test_get_main_readme_file_missing(translator):
    # Assert
    assert translator.get_main_readme_file() == ""


def test_save_translated_readme_creates_file(translator):
    # Arrange
    translation = {"suffix": "fr", "content": "bonjour"}

    # Act
    translator.save_translated_readme(translation)

    # Assert
    file_path = os.path.join(translator.base_path, "README_fr.md")
    assert os.path.exists(file_path)
    assert "bonjour" in open(file_path).read()


def test_save_translated_readme_skips_empty(translator, caplog):
    # Act
    translator.save_translated_readme({"suffix": "fr", "content": ""})

    # Assert
    assert "skipping save" in caplog.text.lower()


def test_set_default_translated_readme_symlink(translator):
    # Arrange
    source = os.path.join(translator.base_path, "README_fr.md")
    with open(source, "w") as f:
        f.write("content")

    translation = {"suffix": "fr"}

    # Act
    translator.set_default_translated_readme(translation)

    # Assert
    target = os.path.join(translator.base_path, ".github", "README.md")
    assert os.path.exists(target)


def test_set_default_translated_readme_copy_on_error(translator):
    # Arrange
    source = os.path.join(translator.base_path, "README_fr.md")
    with open(source, "w") as f:
        f.write("content")

    translation = {"suffix": "fr"}

    # Act
    with patch("os.symlink", side_effect=OSError("no symlink")):
        translator.set_default_translated_readme(translation)

    # Assert
    target = os.path.join(translator.base_path, ".github", "README.md")
    assert os.path.exists(target)
    assert not os.path.islink(target)


@pytest.mark.asyncio
async def test_translate_readme_request_async_valid_json(translator):
    # Arrange
    response = {"content": "text", "suffix": "fr"}
    translator.model_handler.async_send_and_parse = AsyncMock(return_value=response)

    # Act
    result = await translator.translate_readme_request_async("hello", "French", asyncio.Semaphore(1))

    # Assert
    assert result["content"] == "text"
    assert result["suffix"] == "fr"
    assert result["target_language"] == "French"


@pytest.mark.asyncio
async def test_translate_readme_request_async_invalid_json(translator, caplog):
    # Arrange
    translator.model_handler.async_send_and_parse = AsyncMock(return_value={})

    # Act
    result = await translator.translate_readme_request_async("hello", "French", asyncio.Semaphore(1))

    # Assert
    assert result["suffix"] == "fr"
    assert result["target_language"] == "French"


@pytest.mark.asyncio
async def test_translate_readme_async_runs(translator, tmp_path):
    # Arrange
    readme = tmp_path / "README.md"
    readme.write_text("hello readme")

    resp = json.dumps({"content": "bonjour", "suffix": "fr"})
    translator.model_handler.async_request = AsyncMock(return_value=resp)

    # Act
    await translator.translate_readme_async()

    # Assert
    readme_fr = tmp_path / "README_fr.md"
    assert readme_fr.exists()
    target = tmp_path / ".github" / "README.md"
    assert target.exists()
