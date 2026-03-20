import asyncio
import json
import os
from unittest.mock import patch, AsyncMock

import pytest

import osa_tool.operations.docs.readme_translation.readme_translator as rt


@pytest.fixture
def translator(tmp_path, mock_config_manager, mock_repository_metadata):
    """
    Initializes and configures a ReadmeTranslator instance for testing purposes.
    
    Args:
        tmp_path: The temporary file system path to be used as the base path for the translator.
        mock_config_manager: A mocked configuration manager to handle settings.
        mock_repository_metadata: A mocked metadata object containing repository information.
    
    Returns:
        ReadmeTranslator: A configured instance of ReadmeTranslator with the specified base path and target languages.
    
    Why:
        This method is specifically designed for testing scenarios where a ReadmeTranslator instance needs to be created with controlled dependencies and a temporary file system location. It allows for isolated testing of the translator's functionality without affecting actual file systems or requiring real configuration data. The target languages ["fr", "de"] are hardcoded to provide consistent test conditions for translation operations.
    """
    t = rt.ReadmeTranslator(mock_config_manager, mock_repository_metadata, ["fr", "de"])
    t.base_path = tmp_path
    return t


def test_get_main_readme_file_found(translator, tmp_path):
    """
    Verifies that the _get_main_readme_file method correctly returns the content of the README.md file when it exists in the repository root.
    
    This test ensures the method reads and returns the file content as expected when the README.md is present. It does not test error cases or missing files.
    
    Args:
        translator: The ReadmeTranslator instance being tested.
        tmp_path: A pytest fixture providing a temporary directory path for file operations. The test creates a README.md file in this directory with sample content.
    
    Returns:
        None.
    """
    # Arrange
    readme = tmp_path / "README.md"
    readme.write_text("hello readme")

    # Assert
    assert translator._get_main_readme_file() == "hello readme"


def test_get_main_readme_file_missing(translator):
    """
    Verifies that the method returns an empty string when the main README file is missing.
    This test ensures the translator gracefully handles the absence of a primary README.md file in the repository root, returning an empty string instead of raising an error or returning invalid content.
    
    Args:
        translator: An instance of the ReadmeTranslator class being tested.
    """
    # Assert
    assert translator._get_main_readme_file() == ""


def test_save_translated_readme_creates_file(translator):
    """
    Verifies that the _save_translated_readme method correctly creates a file with the expected content.
    
    This test ensures that when a translation dictionary is provided, the method writes the translated content to a properly named file in the expected location.
    
    Args:
        translator: The translator instance used to save the README file and provide the base path for verification. The instance must have a _save_translated_readme method and a base_path attribute.
    
    Why:
        This test validates the file‑creation behavior of the translation‑saving logic, confirming that the output file is placed in the correct directory and contains the exact translated text. It is a unit test for the file‑system interaction of the translation pipeline.
    """
    # Arrange
    translation = {"suffix": "fr", "content": "bonjour"}

    # Act
    translator._save_translated_readme(translation)

    # Assert
    file_path = os.path.join(translator.base_path, "README_fr.md")
    assert os.path.exists(file_path)
    assert "bonjour" in open(file_path).read()


def test_save_translated_readme_skips_empty(translator, caplog):
    """
    Verifies that the translation saving process is skipped when the content is empty.
    This ensures that no unnecessary files are created and that the system logs an appropriate message.
    
    Args:
        translator: The ReadmeTranslator instance being tested.
        caplog: The pytest fixture used to capture log output for assertion.
    """
    # Act
    translator._save_translated_readme({"suffix": "fr", "content": ""})

    # Assert
    assert "skipping save" in caplog.text.lower()


def test_set_default_translated_readme_symlink(translator):
    """
    Verifies that the translator correctly creates a symlink for the default translated README.
    
    This test case simulates the creation of a French translation file, invokes the internal
    method to set the default translated README, and asserts that a symlink is successfully
    created at the expected destination path within the .github directory.
    The test ensures the symlink (or a copy as a fallback) is properly created so that
    the default README in the .github directory points to the first available translation.
    
    Args:
        translator: The translator instance used to manage README translations and file paths.
    """
    # Arrange
    source = os.path.join(translator.base_path, "README_fr.md")
    with open(source, "w") as f:
        f.write("content")

    translation = {"suffix": "fr"}

    # Act
    translator._set_default_translated_readme(translation)

    # Assert
    target = os.path.join(translator.base_path, ".github", "README.md")
    assert os.path.exists(target)


def test_set_default_translated_readme_copy_on_error(translator):
    """
    Verifies that the translator falls back to copying the README file when a symlink creation fails.
    
    This test ensures that if an `OSError` occurs during the symlink process (e.g., on systems where symlinks are not supported), the `_set_default_translated_readme` method correctly creates a physical copy of the translated README file in the `.github` directory instead of failing.
    
    Args:
        translator: The translator instance used to manage README translations and file operations.
    
    Why:
        This fallback mechanism is crucial for cross-platform compatibility, as symlinks may not be supported on all systems (e.g., some Windows configurations). The test validates that the translator gracefully handles such failures by providing a functional alternative.
    """
    # Arrange
    source = os.path.join(translator.base_path, "README_fr.md")
    with open(source, "w") as f:
        f.write("content")

    translation = {"suffix": "fr"}

    # Act
    with patch("os.symlink", side_effect=OSError("no symlink")):
        translator._set_default_translated_readme(translation)

    # Assert
    target = os.path.join(translator.base_path, ".github", "README.md")
    assert os.path.exists(target)
    assert not os.path.islink(target)


@pytest.mark.asyncio
async def test_translate_readme_request_async_valid_json(translator):
    """
    Tests the asynchronous translation request functionality with a valid JSON response.
    
    This test verifies that the asynchronous translation request correctly processes a valid JSON response from the model handler, ensuring the returned result contains the expected content, language suffix, and target language. It mocks the asynchronous model call to simulate a successful translation response.
    
    Args:
        translator: The translator instance being tested, containing a mocked model handler.
    
    Returns:
        None.
    """
    # Arrange
    response = {"content": "text", "suffix": "fr"}
    translator.model_handler.async_send_and_parse = AsyncMock(return_value=response)

    # Act
    result = await translator._translate_readme_request_async("hello", "French", asyncio.Semaphore(1))

    # Assert
    assert result["content"] == "text"
    assert result["suffix"] == "fr"
    assert result["target_language"] == "French"


@pytest.mark.asyncio
async def test_translate_readme_request_async_invalid_json(translator, caplog):
    """
    Tests the asynchronous README translation request when the model returns an invalid or empty JSON response.
    
    This test verifies that the translation method handles malformed or empty JSON from the model gracefully. It ensures the method still returns a valid result structure with the correct language suffix and target language, even when the underlying model provides no usable translation content.
    
    Args:
        translator: The translator instance being tested, containing a mocked model handler.
        caplog: The pytest fixture used to capture log output for assertion.
    
    Returns:
        None.
    """
    # Arrange
    translator.model_handler.async_send_and_parse = AsyncMock(return_value={})

    # Act
    result = await translator._translate_readme_request_async("hello", "French", asyncio.Semaphore(1))

    # Assert
    assert result["suffix"] == "fr"
    assert result["target_language"] == "French"


@pytest.mark.asyncio
async def test_translate_readme_async_runs(translator, tmp_path):
    """
    Verifies that the asynchronous README translation process correctly generates translated files and moves the original to the expected directory.
    
    This test ensures the translation workflow creates a language‑specific copy (e.g., README_fr.md) and relocates the original README.md to a `.github` subdirectory, confirming the file‑handling behavior of the async translation method.
    
    Args:
        translator: The translator instance being tested, containing the model handler and translation logic.
        tmp_path: A pytest fixture providing a temporary directory path for file system operations.
    
    Returns:
        None.
    """
    # Arrange
    readme = tmp_path / "README.md"
    readme.write_text("hello readme")

    resp = json.dumps({"content": "bonjour", "suffix": "fr"})
    translator.model_handler.async_request = AsyncMock(return_value=resp)

    # Act
    await translator._translate_readme_async()

    # Assert
    readme_fr = tmp_path / "README_fr.md"
    assert readme_fr.exists()
    target = tmp_path / ".github" / "README.md"
    assert target.exists()
