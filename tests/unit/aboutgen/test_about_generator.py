from unittest.mock import Mock, patch

import pytest

from osa_tool.aboutgen.about_generator import AboutGenerator


def test_init(about_generator, mock_config_loader):
    assert about_generator.config == mock_config_loader.config
    assert about_generator.repo_url == "https://github.com/test/repo"
    assert about_generator._content is None


def test_generate_about_content(about_generator, mocker):
    mock_desc = "Test description"
    mock_homepage = "https://test.com"
    mock_topics = ["test", "python"]

    mocker.patch.object(about_generator, "generate_description", return_value=mock_desc)
    mocker.patch.object(about_generator, "detect_homepage", return_value=mock_homepage)
    mocker.patch.object(about_generator, "generate_topics", return_value=mock_topics)

    about_generator.generate_about_content()

    assert about_generator._content == {
        "description": mock_desc,
        "homepage": mock_homepage,
        "topics": mock_topics,
    }


def test_generate_description_from_metadata(about_generator, mock_metadata):
    mock_metadata.description = "Existing description"
    about_generator.metadata = mock_metadata

    result = about_generator.generate_description()
    assert result == "Existing description"


def test_generate_description_from_readme(about_generator, sample_readme_content, mocker):
    about_generator.metadata = mocker.Mock()
    about_generator.metadata.description = None

    about_generator.readme_content = sample_readme_content

    mock_response = "Generated description"
    mocker.patch.object(about_generator.model_handler, "send_request", return_value=mock_response)

    result = about_generator.generate_description()

    assert result == mock_response
    about_generator.model_handler.send_request.assert_called_once()


def test_generate_topics_with_existing(about_generator, mock_metadata):
    mock_metadata.topics = ["python", "testing"]
    about_generator.metadata = mock_metadata

    result = about_generator.generate_topics(amount=2)
    assert result == ["python", "testing"]


def test_generate_topics_new(about_generator, mocker):
    about_generator.metadata = mocker.Mock()
    about_generator.metadata.topics = []
    mock_response = "python,testing,automation"

    mocker.patch.object(about_generator.model_handler, "send_request", return_value=mock_response)
    mocker.patch.object(about_generator, "_validate_github_topics", return_value=["python", "testing"])
    result = about_generator.generate_topics()

    assert set(result) == {"python", "testing"}
    about_generator.model_handler.send_request.assert_called_once()
    about_generator._validate_github_topics.assert_called_once_with(["python", "testing", "automation"])


def test_detect_homepage_from_metadata(about_generator, mock_metadata):
    mock_metadata.homepage_url = "https://test.com"
    about_generator.metadata = mock_metadata

    result = about_generator.detect_homepage()
    assert result == "https://test.com"


def test_detect_homepage_from_readme(about_generator, sample_readme_content, mocker):
    about_generator.readme_content = sample_readme_content
    about_generator.metadata.homepage_url = None

    urls = ["https://docs.test-project.com", "https://test-project.com"]
    mocker.patch.object(about_generator, "_extract_readme_urls", return_value=urls)
    mocker.patch.object(about_generator, "_analyze_urls", return_value=urls)

    result = about_generator.detect_homepage()
    assert result == "https://docs.test-project.com"


def test_extract_readme_urls(about_generator, sample_readme_content):
    result = about_generator._extract_readme_urls(sample_readme_content)
    expected = ["https://docs.test-project.com", "https://test-project.com"]
    assert set(result) == set(expected)


def test_get_about_section_message(about_generator):
    content = {
        "description": "Test description",
        "homepage": "https://test.com",
        "topics": ["python", "testing"],
    }
    about_generator._content = content

    message = about_generator.get_about_section_message()
    assert "Test description" in message
    assert "https://test.com" in message
    assert "`python`" in message
    assert "`testing`" in message
