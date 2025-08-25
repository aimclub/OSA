from unittest.mock import MagicMock, patch

import pytest

from osa_tool.aboutgen.about_generator import AboutGenerator


def test_about_generator_init(
    mock_config_loader,
    load_metadata_about_generator,
    mock_readme_content_aboutgen,
    mock_model_handler_aboutgen,
):
    # Act
    generator = AboutGenerator(mock_config_loader)

    # Assert
    assert generator.config == mock_config_loader.config
    assert generator.metadata == load_metadata_about_generator.return_value
    assert generator.readme_content == "Sample README"
    assert generator.platform == "github"
    assert hasattr(generator.prompts, "description")
    assert generator.model_handler.send_request("test") == "Mocked model output"


def test_generate_description(
    mock_config_loader,
    load_metadata_about_generator,
    mock_model_handler_aboutgen,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)
    generator.metadata.description = ""

    # Act
    description = generator.generate_description()

    # Assert
    assert isinstance(description, str)
    assert description == "Mocked model output"
    assert len(description) <= 350


def test_generate_description_exists(
    mock_config_loader,
    load_metadata_about_generator,
    mock_model_handler_aboutgen,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)

    # Act
    description = generator.generate_description()

    # Assert
    assert isinstance(description, str)
    assert description == generator.metadata.description
    assert len(description) <= 350


def test_generate_description_no_readme(
    mock_config_loader,
    load_metadata_about_generator,
    mock_model_handler_aboutgen,
    caplog,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)
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
    mock_config_loader,
    load_metadata_about_generator,
    mock_model_handler_aboutgen,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)
    generator.metadata.topics = []
    mock_model_handler_aboutgen.send_request.return_value = "python, open source, git tools"
    generator._validate_topics = MagicMock(return_value=["python", "open-source", "git-tools"])

    # Act
    topics = generator.generate_topics()

    # Assert
    assert isinstance(topics, list)
    assert "python" in topics
    assert "open-source" in topics
    assert all(isinstance(t, str) for t in topics)
    assert len(topics) <= 7
    generator._validate_topics.assert_called_once()


def test_generate_topics_existing(
    mock_config_loader,
    load_metadata_about_generator,
    mock_model_handler_aboutgen,
):
    # Arrange
    existing = ["python", "opensource", "ai", "ml", "data", "devtools", "api"]
    generator = AboutGenerator(mock_config_loader)
    generator.metadata.topics = existing

    # Act
    topics = generator.generate_topics()

    # Assert
    mock_model_handler_aboutgen.send_request.assert_not_called()
    assert topics == existing


def test_generate_topics_llm_exception_returns_empty(
    mock_config_loader,
    load_metadata_about_generator,
    mock_model_handler_aboutgen,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)
    generator.metadata.topics = []
    mock_model_handler_aboutgen.send_request.side_effect = Exception("LLM error")

    # Act
    topics = generator.generate_topics()

    # Assert
    assert topics == []


def test_detect_homepage_from_metadata(
    mock_config_loader,
    load_metadata_about_generator,
    mock_readme_content_aboutgen,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)

    # Act
    homepage = generator.detect_homepage()

    # Assert
    assert homepage == load_metadata_about_generator.return_value.homepage_url


def test_detect_homepage_from_readme(
    mock_config_loader,
    load_metadata_about_generator,
    mock_model_handler_aboutgen,
):
    # Arrange
    mock_model_handler_aboutgen.send_request.return_value = "https://my-site.org"
    generator = AboutGenerator(mock_config_loader)
    generator.metadata.homepage_url = ""
    generator.readme_content = "Visit us at https://my-site.org for more info."

    # Act
    homepage = generator.detect_homepage()

    # Assert
    assert homepage == "https://my-site.org"


def test_detect_homepage_not_found(
    mock_config_loader,
    load_metadata_about_generator,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)
    generator.metadata.homepage_url = ""
    generator.readme_content = "No link here."

    # Act
    homepage = generator.detect_homepage()

    # Assert
    assert homepage == ""


def test_extract_readme_urls():
    # Arrange
    readme = """
    This is a README with some URLs:
    - https://example.com/page1
    - http://test.org/resource
    - https://example.com/page1  # duplicate URL
    """
    expected_urls = {"https://example.com/page1", "http://test.org/resource"}

    # Act
    urls = AboutGenerator._extract_readme_urls(readme)

    # Assert
    assert set(urls) == expected_urls


def test_analyze_urls(
    mock_config_loader,
    load_metadata_about_generator,
    mock_model_handler_aboutgen,
):
    # Arrange
    urls = ["https://example.com", "http://test.org"]
    fake_response = "https://example.com, http://test.org"
    generator = AboutGenerator(mock_config_loader)
    generator.model_handler.send_request.return_value = fake_response
    expected_prompt = generator.prompts.analyze_urls.format(project_url=generator.repo_url, urls=", ".join(urls))

    # Act
    result = generator._analyze_urls(urls)

    # Assert
    generator.model_handler.send_request.assert_called_once_with(expected_prompt)
    assert result == ["https://example.com", "http://test.org"]


@patch("osa_tool.aboutgen.about_generator.requests.get")
@patch("osa_tool.aboutgen.about_generator.time.sleep", return_value=None)
def test_validate_github_topics_with_factory(
    mock_sleep,
    mock_get,
    mock_config_loader,
    load_metadata_about_generator,
    mock_requests_response_factory,
):
    # Arrange
    json_data = {"total_count": 2, "items": [{"name": "topic1"}, {"name": "topic2"}]}
    mock_get.return_value = mock_requests_response_factory(200, json_data)
    topics = ["topic1", "topic2"]
    generator = AboutGenerator(mock_config_loader)

    # Act
    validated = generator._validate_github_topics(topics)

    # Assert
    assert "topic1" in validated
    assert "topic2" in validated
    assert mock_get.call_count == len(topics)


@patch("osa_tool.aboutgen.about_generator.requests.get")
@patch("osa_tool.aboutgen.about_generator.time.sleep", return_value=None)
def test_validate_github_topics_raises_http_error(
    mock_sleep,
    mock_get,
    mock_config_loader,
    load_metadata_about_generator,
    mock_requests_response_factory,
):
    # Arrange
    mock_get.return_value = mock_requests_response_factory(403)
    topics = ["topic1"]
    generator = AboutGenerator(mock_config_loader)

    # Act
    validated = generator._validate_github_topics(topics)

    # Assert
    assert validated == []
    mock_get.assert_called_once()


@pytest.mark.parametrize(
    "mock_config_loader, method_name, expected_result",
    [
        ("github", "_validate_github_topics", ["topic1_validated"]),
        ("gitlab", "_validate_gitlab_topics", ["topic2_validated"]),
        ("gitverse", "_validate_gitverse_topics", ["topic3", "topic4"]),
    ],
    indirect=["mock_config_loader"],
)
def test_validate_topics_platforms(
    mocker, load_metadata_about_generator, mock_config_loader, method_name, expected_result
):
    # Arrange
    topics = ["topic1", "topic2"]
    generator = AboutGenerator(mock_config_loader)

    # Patch the specific validator method
    mock_method = mocker.patch.object(AboutGenerator, method_name, return_value=expected_result)

    # Act
    result = generator._validate_topics(topics)

    # Assert
    mock_method.assert_called_once_with(topics)
    assert result == expected_result


def test_generate_about_content_once_only(
    mock_config_loader,
    load_metadata_about_generator,
    mock_readme_content_aboutgen,
    mock_model_handler_aboutgen,
    mocker,
    caplog,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)
    mocker.patch.object(generator, "generate_description", return_value="Test description")
    mocker.patch.object(generator, "detect_homepage", return_value="https://example.com")
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
    mock_config_loader,
    load_metadata_about_generator,
    mocker,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)
    mock_generate = mocker.patch.object(generator, "generate_about_content")

    # Act
    generator._content = None
    _ = generator.get_about_content()

    # Assert
    mock_generate.assert_called_once()


def test_get_about_section_message_formatting(
    mock_config_loader,
    load_metadata_about_generator,
    caplog,
):
    # Arrange
    generator = AboutGenerator(mock_config_loader)
    generator._content = {
        "description": "Test repo",
        "homepage": "https://example.com",
        "topics": ["ai", "ml"],
    }
    caplog.set_level("INFO")

    # Act
    message = generator.get_about_section_message()

    # Assert
    assert "Description: Test repo" in message
    assert "Homepage: https://example.com" in message
    assert "Topics: `ai`, `ml`" in message
    assert "Started generating About section content." in caplog.text
    assert "Finished generating About section content." in caplog.text
