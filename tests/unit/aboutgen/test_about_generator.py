from unittest.mock import MagicMock

import pytest

from osa_tool.operations.docs.about_generation.about_generator import AboutGenerator
from osa_tool.utils.prompts_builder import PromptBuilder


@pytest.fixture
def mock_git_agent(mock_repository_metadata):
    """
    Mock a GitAgent instance with predefined metadata and a mocked validate_topics method.
    
    This function is used in testing to simulate a GitAgent object without requiring
    a real repository or network connection. It allows tests to control the agent's
    metadata and the output of its validate_topics method.
    
    Args:
        mock_repository_metadata: The metadata to assign to the mocked GitAgent's
            metadata attribute. This typically mimics the structure of repository
            metadata used by the actual GitAgent.
    
    Returns:
        A MagicMock object configured as a GitAgent. The mock has:
            - A `metadata` attribute set to the provided mock_repository_metadata.
            - A `validate_topics` method that, when called, returns a fixed list
              containing the string "validated-topic".
    """
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
    """
    Tests the initialization of the AboutGenerator class to ensure all attributes are correctly assigned.
    
    This test verifies that the AboutGenerator constructor properly stores its dependencies and loads the required data. It ensures the generator is ready to produce content by confirming that configuration, repository metadata, README content, and the model handler are correctly initialized and functional.
    
    Args:
        mock_config_manager: A mocked configuration manager instance.
        mock_readme_content_aboutgen: A fixture providing mock README content.
        mock_model_handler_aboutgen: A fixture providing a mock model handler.
        mock_git_agent: A mocked git agent instance containing repository metadata.
    
    Class Fields Verified:
        config_manager: Stores the configuration manager instance for settings access.
        metadata: Stores repository metadata retrieved from the git agent.
        readme_content: Stores the content of the project's README file, which is mocked to a fixed sample value for testing.
        model_handler: An instance of the model handler used for generating content; its functionality is verified by checking a mocked response.
    
    Why:
        The test confirms that the AboutGenerator correctly integrates its dependencies and initializes its state. This is critical because the generator relies on these components to produce accurate documentation. The mock fixtures isolate the test from external systems, ensuring reliability and speed.
    """
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
    """
    Verifies that the `_generate_description` method of the `AboutGenerator` class correctly produces a repository description string.
    
    This test ensures the method returns a valid string that meets length constraints and matches expected mocked output, confirming the description generation logic works as intended.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used for initialization.
        mock_model_handler_aboutgen: A mocked model handler used to simulate AI model responses.
        mock_git_agent: A mocked git agent used to simulate repository interactions.
    
    Returns:
        None.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.description = ""

    # Act
    description = generator._generate_description()

    # Assert
    assert isinstance(description, str)
    assert description == "Mocked model output"
    assert len(description) <= 350


def test_generate_description_exists(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    """
    Verifies that the _generate_description method returns a string description that matches the generator's metadata and adheres to length constraints.
    
    This test ensures the generated description is a valid string, corresponds to the generator's stored metadata, and does not exceed the maximum allowed length.
    
    Args:
        mock_config_manager: A mocked configuration manager instance.
        mock_model_handler_aboutgen: A mocked model handler instance for description generation.
        mock_git_agent: A mocked git agent instance for repository interactions.
    
    Returns:
        None: This is a test method and does not return a value.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)

    # Act
    description = generator._generate_description()

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
    """
    Tests that `_generate_description` returns an empty string and logs a warning when no README content is available.
    
    This test verifies the behavior when the AboutGenerator instance has no README content,
    ensuring that the description generation is skipped, a warning is logged, and no model request is made.
    
    Args:
        mock_config_manager: Mocked configuration manager dependency.
        mock_model_handler_aboutgen: Mocked model handler for generating descriptions.
        mock_git_agent: Mocked git agent for repository operations.
        caplog: Pytest fixture to capture log messages.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.description = ""
    generator.readme_content = ""
    caplog.set_level("WARNING")

    # Act
    description = generator._generate_description()

    # Assert
    assert description == ""
    assert "No README content found. Cannot generate description." in caplog.text
    generator.model_handler.send_request.assert_not_called()


def test_generate_topics(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    """
    Verifies that the topic generation process correctly parses model output and validates topics through the git agent.
    
    This test ensures that the AboutGenerator's internal topic generation method:
    1. Parses a simulated AI model response string into a list of candidate topics.
    2. Uses the git agent to validate and normalize these topics (e.g., formatting adjustments).
    3. Returns a list of valid topics that meet the expected constraints (type, length, content).
    
    Args:
        mock_config_manager: Mocked configuration manager for the generator.
        mock_model_handler_aboutgen: Mocked model handler used to simulate AI responses for topic generation. Its send_request method is configured to return a comma-separated string of topics.
        mock_git_agent: Mocked git agent used to validate the generated topics. Its validate_topics method is configured to return a normalized list of topics.
    
    Returns:
        None. This is a test method; assertions are used to verify behavior.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.topics = []
    mock_model_handler_aboutgen.send_request.return_value = "python, open source, git tools"
    mock_git_agent.validate_topics.return_value = ["python", "open-source", "git-tools"]

    # Act
    topics = generator._generate_topics()

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
    """
    Verifies that the topic generation process returns existing topics without calling the model handler if topics are already present in the metadata.
    
    This test ensures that when the repository metadata already contains topics, the generator reuses them and avoids unnecessary API calls to the model handler, optimizing performance and preserving existing data.
    
    Args:
        mock_config_manager: Mock object for managing configuration settings.
        mock_model_handler_aboutgen: Mock object for the model handler responsible for generating content.
        mock_git_agent: Mock object for interacting with Git repository operations.
    
    Returns:
        None: This is a test method and does not return a value.
    """
    # Arrange
    existing = ["python", "opensource", "ai", "ml", "data", "devtools", "api"]
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.topics = existing

    # Act
    topics = generator._generate_topics()

    # Assert
    mock_model_handler_aboutgen.send_request.assert_not_called()
    assert topics == existing


def test_generate_topics_llm_exception_returns_empty(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    """
    Verifies that `_generate_topics` returns an empty list when the LLM model handler raises an exception.
    
    This test ensures the method gracefully handles LLM failures by returning an empty list instead of propagating the error, maintaining robustness in the documentation generation pipeline.
    
    Args:
        mock_config_manager: A mocked configuration manager instance.
        mock_model_handler_aboutgen: A mocked model handler instance configured to raise an exception when `send_request` is called.
        mock_git_agent: A mocked git agent instance.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.topics = []
    mock_model_handler_aboutgen.send_request.side_effect = Exception("LLM error")

    # Act
    topics = generator._generate_topics()

    # Assert
    assert topics == []


def test_detect_homepage_from_metadata(
    mock_config_manager,
    mock_git_agent,
):
    """
    Verifies that the `_detect_homepage` method correctly retrieves the homepage URL when it is already present in the generator's metadata.
    
    WHY: This test ensures the method prioritizes and returns an existing homepage URL from metadata, avoiding unnecessary detection logic when the URL is already known.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used for initializing the generator.
        mock_git_agent: A mocked git agent instance used for initializing the generator.
    
    Returns:
        None.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    expected_homepage = "https://example.com"
    generator.metadata.homepage_url = expected_homepage

    # Act
    homepage = generator._detect_homepage()

    # Assert
    assert homepage == expected_homepage


def test_detect_homepage_from_readme(
    mock_config_manager,
    mock_model_handler_aboutgen,
    mock_git_agent,
):
    """
    Verifies that the homepage URL is correctly detected from the README content using the AboutGenerator.
    
    This test ensures the AboutGenerator's internal detection logic extracts a homepage URL from provided README text, confirming the integration works as expected.
    
    Args:
        mock_config_manager: A mock object for managing configuration settings.
        mock_model_handler_aboutgen: A mock object for handling AI model requests related to about generation.
        mock_git_agent: A mock object for interacting with Git repositories.
    
    Why:
        The test validates that the detection method works independently of any AI model response, focusing on the extraction logic from plain text. It uses a mocked AI model to isolate the test from external API dependencies.
    """
    # Arrange
    mock_model_handler_aboutgen.send_request.return_value = "https://my-site.org"
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.homepage_url = ""
    generator.readme_content = "Visit us at https://my-site.org for more info."

    # Act
    homepage = generator._detect_homepage()

    # Assert
    assert homepage == "https://my-site.org"


def test_detect_homepage_not_found(
    mock_config_manager,
    mock_git_agent,
):
    """
    Verifies that the `_detect_homepage` method returns an empty string when no homepage URL is provided in the metadata and no link is found in the README content.
    
    This test ensures the detection logic correctly handles the absence of a homepage by returning an empty string, preventing false positives when no valid URL is available.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the generator.
        mock_git_agent: A mocked git agent instance used to initialize the generator.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.homepage_url = ""
    generator.readme_content = "No link here."

    # Act
    homepage = generator._detect_homepage()

    # Assert
    assert homepage == ""


def test_detect_homepage_no_readme(
    mock_config_manager,
    mock_git_agent,
    caplog,
):
    """
    Verifies that the homepage detection returns an empty string when no README content is available.
    This test ensures the system gracefully handles missing READMEs by logging a warning and returning an empty string instead of failing or returning incorrect data.
    
    Args:
        mock_config_manager: A mocked configuration manager instance.
        mock_git_agent: A mocked git agent instance.
        caplog: The pytest fixture used to capture log output.
    
    Returns:
        None: This is a test method and does not return a value.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    generator.metadata.homepage_url = ""
    generator.readme_content = ""
    caplog.set_level("WARNING")

    # Act
    homepage = generator._detect_homepage()

    # Assert
    assert homepage == ""
    assert "No README content found. Cannot detect homepage." in caplog.text


def test_extract_readme_urls():
    """
    Tests the extraction of absolute URLs from README content.
    
    This test verifies that the helper method _extract_readme_urls correctly
    identifies and returns a set of unique absolute URLs from a given README
    string. It ensures that duplicate URLs are removed and only absolute URLs are captured.
    
    Args:
        None.
    
    Returns:
        None.
    """
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
    """
    Tests the _analyze_urls method of AboutGenerator.
    
    This test verifies that the _analyze_urls method correctly interacts with the model handler to analyze a list of URLs. It sets up a mock response, calls the method, and asserts that the model handler was called with the expected prompt and that the method returns the processed URLs. The test ensures the method properly formats the prompt with the project URL and the provided URL list, sends it to the model, and cleans the model's response into a standardized list.
    
    Args:
        mock_config_manager: A mocked configuration manager.
        mock_model_handler_aboutgen: A mocked model handler for the AboutGenerator.
        mock_git_agent: A mocked git agent.
    """
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
    """
    Verify that the About section content is generated only once and subsequent calls are skipped.
    
    This test ensures the AboutGenerator's internal caching mechanism works correctly:
    after the first successful generation, subsequent calls should not regenerate content
    and should log a warning instead.
    
    Args:
        mock_config_manager: Mocked configuration manager for the generator.
        mock_readme_content_aboutgen: Mocked README content provider.
        mock_model_handler_aboutgen: Mocked AI model handler.
        mock_git_agent: Mocked git agent for repository interactions.
        mocker: Pytest-mock fixture for patching objects.
        caplog: Pytest fixture to capture log output.
    
    Steps performed:
        1. Creates an AboutGenerator instance with mocked dependencies.
        2. Patches internal generation methods to return fixed test data.
        3. Calls generate_about_content twice.
        4. Verifies that the internal content remains unchanged between calls.
        5. Confirms that a specific warning log is produced on the second call.
    """
    # Arrange
    generator = AboutGenerator(mock_config_manager, mock_git_agent)
    mocker.patch.object(generator, "_generate_description", return_value="Test description")
    mocker.patch.object(generator, "_generate_topics", return_value=["topic1", "topic2"])
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
    """
    Verifies that the `get_about_content` method triggers a new content generation process when the internal content cache is missing.
    
    This test ensures that the generator correctly handles a cache miss by calling the generation method to populate the cache, which is necessary for on-demand content creation and performance optimization.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the generator.
        mock_git_agent: A mocked Git agent instance used to initialize the generator.
        mocker: The pytest-mock fixture used for patching the generation method.
    """
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
    """
    Verifies that the `get_about_section_message` method correctly formats the repository's description, homepage, and topics into a single string and logs the process.
    
    This test ensures the About section generator produces a properly formatted output string containing the repository's metadata and that the generation process is logged at the INFO level.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the generator.
        mock_git_agent: A mocked Git agent instance used to initialize the generator.
        caplog: A pytest fixture used to capture and inspect log messages.
    """
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
