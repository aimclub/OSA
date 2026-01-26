from unittest.mock import MagicMock

import pytest

from osa_tool.aboutgen.about_generator import AboutGenerator
from osa_tool.utils.prompts_builder import PromptBuilder


@pytest.fixture
def mock_git_agent(mock_repository_metadata):
    """Mock GitAgent with metadata and validate_topics."""
    git_agent = MagicMock()
    git_agent.metadata = mock_repository_metadata
    git_agent.validate_topics = MagicMock(return_value=["validated-topic"])
    return git_agent


def test_about_generator_init(
    mock_config_manager,
    mock_readme_content_aboutgen,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    # Act
    generator = AboutGenerator(mock_config_manager, mock_git_agent)

    # Assert
    assert generator.config_manager == mock_config_manager
    assert generator.metadata == mock_git_agent.metadata
    assert generator.readme_content == "Sample README"
    assert generator.model_handler.send_request("test") == "Mocked model output"


def test_generate_description(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.description = ""

    # Act
    description = generator.generate_description()

    # Assert
    assert isinstance(description, str)
    assert description == "Mocked model output"
    assert len(description) <= 350


def test_generate_description_exists(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)

    # Act
    description = generator.generate_description()

    # Assert
    assert isinstance(description, str)
    assert description == generator.metadata.description
    assert len(description) <= 350


def test_generate_description_no_readme(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
    caplog,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.description = ""
    generator.readme_content = ""
    caplog.set_level("WARNING")

    # Act
    description = generator.generate_description()

    # Assert
    assert description == ""
    assert "No README content found. Cannot generate description." in caplog.text
    generator.model_handler.send_request.assert_not_called()


def test_generate_topics(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.topics = []
    mock_model_handler_aboutgen.send_request.return_value = "python, open source, git tools"
    mock_git_agent.validate_topics.return_value = ["python", "open-source", "git-tools"]

    # Act
    topics = generator.generate_topics()

    # Assert
    assert isinstance(topics, list)
    assert "python" in topics
    assert "open-source" in topics
    assert all(isinstance(t, str) for t in topics)
    assert len(topics) <= 7


def test_generate_topics_existing(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    # Arrange
    existing = ["python", "opensource", "ai", "ml", "data", "devtools", "api"]
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.topics = existing

    # Act
    topics = generator.generate_topics()

    # Assert
    mock_model_handler_aboutgen.send_request.assert_not_called()
    assert topics == existing


def test_generate_topics_llm_exception_returns_empty(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.topics = []
    mock_model_handler_aboutgen.send_request.side_effect = Exception("LLM error")

    # Act
    topics = generator.generate_topics()

    # Assert
    assert topics == []


def test_detect_homepage_from_metadata(
    mock_config_manager,
    mock_git_agent,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    expected_homepage = "https://example.com"
    generator.metadata.homepage_url = expected_homepage

    # Act
    homepage = generator.detect_homepage()

    # Assert
    assert homepage == expected_homepage


def test_detect_homepage_from_readme(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    # Arrange
    mock_model_handler_aboutgen.send_request.return_value = "https://my-site.org"
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.homepage_url = ""
    generator.readme_content = "Visit us at https://my-site.org for more info."

    # Act
    homepage = generator.detect_homepage()

    # Assert
    assert homepage == "https://my-site.org"


def test_detect_homepage_not_found(
    mock_config_manager,
    mock_git_agent,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.homepage_url = ""
    generator.readme_content = "No link here."

    # Act
    homepage = generator.detect_homepage()

    # Assert
    assert homepage == ""


def test_detect_homepage_no_readme(
    mock_config_manager,
    mock_git_agent,
    caplog,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.homepage_url = ""
    generator.readme_content = ""
    caplog.set_level("WARNING")

    # Act
    homepage = generator.detect_homepage()

    # Assert
    assert homepage == ""
    assert "No README content found. Cannot detect homepage." in caplog.text


def test_extract_readme_urls():
    # Arrange
    readme = """
    This is a README with some URLs:
    - https://example.com/page1  
    - http://test.org/resource
    - https://example.com/page1
    """
    expected_urls = {"https://example.com/page1", "http://test.org/resource"}

    # Act
    urls = AboutGenerator._extract_readme_urls(readme)

    # Assert
    assert set(urls) == expected_urls


def test_analyze_urls(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    # Arrange
    urls = ["https://example.com", "http://test.org"]
    fake_response = "https://example.com  , http://test.org"
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.model_handler.send_request.return_value = fake_response
    expected_prompt = PromptBuilder.render(
        generator.prompts.get("about_section.analyze_urls"), project_url=generator.repo_url, urls=", ".join(urls)
    )

    # Act
    result = generator._analyze_urls(urls)

    # Assert
    generator.model_handler.send_request.assert_called_once_with(expected_prompt)
    assert result == ["https://example.com", "http://test.org"]


def test_generate_about_content_once_only(
    mock_config_manager,
    mock_readme_content_aboutgen,
    mock_model_handler_aboutgen,
    mock_git_agent,
    mocker,
    caplog,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    mocker.patch.object(generator, "generate_description", return_value="Test description")
    mocker.patch.object(generator, "generate_topics", return_value=["topic1", "topic2"])
    caplog.set_level("WARNING")

    # Act
    generator.generate_about_content()
    first_result = generator._content.copy()

    generator.generate_about_content()
    second_result = generator._content.copy()

    # Assert
    assert first_result == second_result
    assert "About section content already generated. Skipping generation." in caplog.text


def test_get_about_content_triggers_generation_if_missing(
    mock_config_manager,
    mock_git_agent,
    mocker,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    mock_generate = mocker.patch.object(generator, "generate_about_content")

    # Act
    generator._content = None
    _ = generator.get_about_content()

    # Assert
    mock_generate.assert_called_once()


def test_get_about_section_message_formatting(
    mock_config_manager,
    mock_git_agent,
    caplog,
):
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator._content = {
        "description": "Test repo",
        "homepage": "https://example.com  ",
        "topics": ["ai", "ml"],
    }
    caplog.set_level("INFO")

    # Act
    message = generator.get_about_section_message()

    # Assert
    assert "Description: Test repo" in message
    assert "Homepage: https://example.com  " in message
    assert "Topics: `ai`, `ml`" in message
    assert "Started generating About section content." in caplog.text
    assert "Finished generating About section content." in caplog.text
