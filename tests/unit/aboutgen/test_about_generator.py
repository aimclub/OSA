from unittest.mock import Mock, patch

import pytest

from osa_tool.aboutgen.about_generator import AboutGenerator


def test_init(about_generator, mock_config_loader):
    """
    Test that AboutGenerator is initialized correctly.
    
    Parameters
    ----------
    about_generator
        The AboutGenerator instance to test.
    mock_config_loader
        Mock configuration loader providing the expected configuration.
    
    Returns
    -------
    None
    """
    assert about_generator.config == mock_config_loader.config
    assert about_generator.repo_url == "https://github.com/test/repo"
    assert about_generator._content is None


def test_generate_about_content(about_generator, mocker):
    """
    Test that AboutGenerator.generate_about_content correctly populates the
        internal `_content` dictionary with description, homepage, and topics.
    
        Parameters
        ----------
        about_generator
            The instance of the class under test. It is expected to have the
            methods `generate_description`, `detect_homepage`, and `generate_topics`,
            as well as a mutable `_content` attribute that will be updated.
        mocker
            Pytest mocker fixture used to patch the methods of `about_generator`
            so that deterministic values are returned during the test.
    
        Returns
        -------
        None
            The function performs assertions on the internal state of
            `about_generator`; it does not return a value.
    """
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
    """
    Test that AboutGenerator.generate_description returns the description from metadata when it is already set.
    
    Args:
        about_generator: The instance of AboutGenerator under test.
        mock_metadata: A mock metadata object with a 'description' attribute.
    
    Returns:
        None
    """
    mock_metadata.description = "Existing description"
    about_generator.metadata = mock_metadata

    result = about_generator.generate_description()
    assert result == "Existing description"


def test_generate_description_from_readme(about_generator, sample_readme_content, mocker):
    """
    Test that the `generate_description` method correctly returns a description generated from the README content when the metadata description is initially unset.
    
    Parameters
    ----------
    about_generator : object
        The instance of the class under test, which contains a `metadata` attribute and a `model_handler` used to generate descriptions.
    sample_readme_content : str
        Sample README text that will be supplied to the generator for description creation.
    mocker : pytest-mock.MockFixture
        Fixture used to create mocks and patch methods during the test.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the generated description matches the mocked response and that the model handler's `send_request` method is called exactly once.
    """
    about_generator.metadata = mocker.Mock()
    about_generator.metadata.description = None

    about_generator.readme_content = sample_readme_content

    mock_response = "Generated description"
    mocker.patch.object(about_generator.model_handler, "send_request", return_value=mock_response)

    result = about_generator.generate_description()

    assert result == mock_response
    about_generator.model_handler.send_request.assert_called_once()


def test_generate_topics_with_existing(about_generator, mock_metadata):
    """
    Test that `generate_topics` returns existing topics when metadata already contains topics.
    
    Args:
        about_generator: The instance of the class under test that has a `generate_topics` method.
        mock_metadata: A mock object representing metadata, which should have a `topics` attribute.
    
    Returns:
        None
    
    This test sets the `mock_metadata.topics` to a predefined list, assigns it to the `about_generator`'s `metadata`, calls `generate_topics` with `amount=2`, and asserts that the returned list matches the predefined topics.
    """
    mock_metadata.topics = ["python", "testing"]
    about_generator.metadata = mock_metadata

    result = about_generator.generate_topics(amount=2)
    assert result == ["python", "testing"]


def test_generate_topics_new(about_generator, mocker):
    """
    Test that the `generate_topics` method correctly processes and validates GitHub topics.
    
    Parameters
    ----------
    about_generator : object
        The instance of the class under test. It is expected to have a `metadata` attribute
        (which contains a `topics` list), a `model_handler` attribute with a `send_request`
        method, and a private `_validate_github_topics` method.
    mocker : pytest fixture
        Provides utilities for creating mocks and patching methods during the test.
    
    Returns
    -------
    None
    """
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
    """
    Test that the `detect_homepage` method correctly retrieves the homepage URL from
    metadata.
    
    This test assigns a known homepage URL to a mock metadata object, injects that
    metadata into the `about_generator` instance, and verifies that calling
    `detect_homepage` returns the expected URL.
    
    Args:
        about_generator: The object under test that contains a `metadata` attribute
            and a `detect_homepage` method.
        mock_metadata: A mock object representing metadata, which must support
            setting a `homepage_url` attribute.
    
    Returns:
        None
    """
    mock_metadata.homepage_url = "https://test.com"
    about_generator.metadata = mock_metadata

    result = about_generator.detect_homepage()
    assert result == "https://test.com"


def test_detect_homepage_from_readme(about_generator, sample_readme_content, mocker):
    """
    Test that the AboutGenerator correctly identifies the homepage URL from the README content.
    
    This test sets up a mock AboutGenerator instance with sample README content and
    ensures that the `detect_homepage` method returns the expected homepage URL.
    It patches the internal URL extraction and analysis methods to return a
    predefined list of URLs, then verifies that the first URL in that list is
    chosen as the homepage.
    
    Args:
        about_generator: The AboutGenerator instance under test.
        sample_readme_content: A string containing the README content to be used
            for URL extraction.
        mocker: A pytest fixture used to patch internal methods of the
            AboutGenerator.
    
    Returns:
        None
    """
    about_generator.readme_content = sample_readme_content
    about_generator.metadata.homepage_url = None

    urls = ["https://docs.test-project.com", "https://test-project.com"]
    mocker.patch.object(about_generator, "_extract_readme_urls", return_value=urls)
    mocker.patch.object(about_generator, "_analyze_urls", return_value=urls)

    result = about_generator.detect_homepage()
    assert result == "https://docs.test-project.com"


def test_extract_readme_urls(about_generator, sample_readme_content):
    """
    Test the extraction of URLs from a README content string.
    
    This test verifies that the private method `_extract_readme_urls` of the
    `about_generator` correctly identifies and returns all URLs present in the
    provided `sample_readme_content`. It compares the resulting list of URLs
    against an expected set of URLs to ensure the extraction logic works as
    intended.
    
    Args:
        about_generator: The instance containing the `_extract_readme_urls`
            method to be tested.
        sample_readme_content: A string representing the content of a README
            file from which URLs should be extracted.
    
    Returns:
        None. The function asserts that the extracted URLs match the expected
        URLs; if the assertion fails, an AssertionError is raised.
    """
    result = about_generator._extract_readme_urls(sample_readme_content)
    expected = ["https://docs.test-project.com", "https://test-project.com"]
    assert set(result) == set(expected)


def test_get_about_section_message(about_generator):
    """
    Test that AboutGenerator.get_about_section_message returns a message containing the description, homepage, and topics formatted with backticks.
    
    Args:
        about_generator: The AboutGenerator instance to test.
    
    Returns:
        None
    
    The test sets the internal _content of about_generator to a sample dictionary and verifies that the resulting message includes the description, homepage URL, and each topic wrapped in backticks.
    """
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
