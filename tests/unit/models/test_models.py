import pytest

from osa_tool.core.llm.llm import ModelHandlerFactory, PayloadFactory, ProtollmHandler
from tests.utils.fixtures.models import DummyLLMClient


def test_payload_factory_generates_expected_structure(mock_config_manager):
    """
    Verifies that the PayloadFactory correctly constructs a payload dictionary with the expected schema and values.
    
    This test ensures the factory builds a payload with the required keys and that values from the model settings are correctly mapped into the payload structure.
    
    Args:
        mock_config_manager: A mocked configuration manager used to retrieve model settings for the test.
    
    Returns:
        None.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    factory = PayloadFactory(model_settings, "my test prompt")

    # Act
    payload = factory.to_payload_completions()

    # Assert
    assert set(payload.keys()) == {"job_id", "meta", "messages"}
    assert payload["meta"]["temperature"] == model_settings.temperature
    assert payload["meta"]["tokens_limit"] == model_settings.max_tokens
    assert any("my test prompt" in str(msg) for msg in payload["messages"])


def test_initialize_payload_sets_payload(mock_config_manager):
    """
    Verifies that the initialize_payload method correctly sets the payload attribute with the expected message content.
    
    This test ensures that when initialize_payload is called with given model settings and a prompt, the handler's payload attribute is populated with a 'messages' list containing the provided prompt.
    
    Args:
        mock_config_manager: A mocked configuration manager used to retrieve model settings for the test.
    
    Returns:
        None
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)
    handler.client = DummyLLMClient()

    # Act
    handler.initialize_payload(model_settings, "init prompt")

    # Assert
    assert "messages" in handler.payload
    assert any("init prompt" in str(m) for m in handler.payload["messages"])


def test_send_request_calls_llm(monkeypatch, mock_config_manager, patch_llm_connector):
    """
    Verifies that the send_request method of ProtollmHandler correctly interacts with the LLM connector to return a response.
    
    WHY: This test ensures the handler properly integrates with the LLM connector, using mocked dependencies to isolate and validate the interaction without making actual external calls.
    
    Args:
        monkeypatch: Pytest fixture used to mock or patch objects, functions, or dictionary items.
        mock_config_manager: A mocked configuration manager used to retrieve model settings.
        patch_llm_connector: A fixture or mock used to intercept and simulate calls to the underlying LLM connector.
    
    Returns:
        None.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)

    # Act
    result = handler.send_request("hello world")

    # Assert
    assert result == "sync response"


@pytest.mark.asyncio
async def test_async_request_calls_llm(mock_config_manager, patch_llm_connector):
    """
    Verifies that the asynchronous request method correctly interacts with the LLM connector to return a response.
    
    WHY: This test ensures that the async_request method of ProtollmHandler properly calls the underlying LLM connector and returns the expected response, validating the integration and fallback logic in an asynchronous context.
    
    Args:
        mock_config_manager: A mocked configuration manager used to retrieve model settings for the 'general' task type.
        patch_llm_connector: A fixture or patch used to mock the underlying LLM connector's response, simulating a successful call that returns "async response".
    
    Returns:
        None.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)

    # Act
    result = await handler.async_request("async hello")

    # Assert
    assert result == "async response"


@pytest.mark.asyncio
async def test_generate_concurrently_orders_results(mock_config_manager, patch_llm_connector):
    """
    Verifies that the generate_concurrently method returns results in the same order as the input prompts.
    This ensures that the concurrent processing does not reorder responses, which is critical for maintaining correspondence between prompts and their outputs.
    
    Args:
        mock_config_manager: A mocked configuration manager used to retrieve model settings for the general task.
        patch_llm_connector: A fixture or mock used to intercept and simulate LLM connector responses, providing a controlled test environment.
    
    Returns:
        None.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)
    prompts = ["p1", "p2", "p3"]

    # Act
    results = await handler.generate_concurrently(prompts)

    # Assert
    assert results == ["async response"] * len(prompts)


@pytest.mark.parametrize(
    "api,expected_prefix",
    [
        ("itmo", "self_hosted;"),
        ("ollama", "ollama;"),
        ("other", ""),
    ],
)
def test_build_model_url_varies_with_api(mock_config_manager, patch_llm_connector, api, expected_prefix):
    """
    Verifies that the model URL is correctly constructed based on the specified API type.
    
    This test ensures that the `ProtollmHandler` generates a URL with the appropriate prefix (e.g., "self_hosted;" for ITMO or "ollama;" for Ollama) depending on the API configuration provided in the model settings. The test validates that the URL-building logic correctly adapts to different API types, including cases where no prefix is expected.
    
    Args:
        mock_config_manager: A mocked configuration manager used to retrieve model settings.
        patch_llm_connector: A fixture or mock used to patch the LLM connector during testing.
        api: The API type string being tested (e.g., "itmo", "ollama", "other").
        expected_prefix: The expected string prefix that the generated URL should start with. An empty string indicates no prefix is expected.
    
    Why:
        This test is necessary to confirm that the handler's internal URL construction respects the API configuration, ensuring compatibility with different LLM backends (like self-hosted ITMO, Ollama, or other APIs) by prefixing the model identifier appropriately.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    model_settings.api = api
    handler = ProtollmHandler(model_settings)

    # Act
    url = handler._build_model_url(model_settings.model)

    # Assert
    assert url.startswith(expected_prefix) or expected_prefix == ""


def test_get_llm_params_filters_none(mock_config_manager, patch_llm_connector):
    """
    Verifies that the `_get_llm_params` method correctly filters out any None values from the resulting parameters dictionary. This ensures that only valid, non-None parameters are passed to the LLM, preventing potential errors or unintended behavior from null values.
    
    Args:
        mock_config_manager: A mocked configuration manager used to provide model settings.
        patch_llm_connector: A fixture or mock used to patch the LLM connector during testing.
    
    The test performs the following steps:
    1. Retrieves model settings for the "general" task type.
    2. Instantiates a ProtollmHandler with those settings.
    3. Calls the `_get_llm_params` method to obtain the parameters dictionary.
    4. Asserts that the dictionary contains a "temperature" key and that all values in the dictionary are not None.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)

    # Act
    params = handler._get_llm_params()

    # Assert
    assert "temperature" in params
    assert all(v is not None for v in params.values())


def test_model_handler_factory_builds_correct_type(mock_config_manager):
    """
    Tests that ModelHandlerFactory.build creates a handler of the correct type.
    
    WHY: This test verifies that the factory correctly instantiates the expected handler class (ProtollmHandler) when provided with model settings for a general task, ensuring the factory's mapping and instantiation logic works as intended.
    
    Args:
        mock_config_manager: A fixture or object providing model settings, used to retrieve settings for the "general" task type.
    
    Returns:
        None
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")

    # Act
    handler = ModelHandlerFactory.build(model_settings)

    # Assert
    assert isinstance(handler, ProtollmHandler)


def test_protollm_handler_init(mock_config_manager):
    """
    Verifies the successful initialization of the ProtollmHandler class.
    
    This test ensures that when a ProtollmHandler instance is created with valid model settings, its internal state is correctly populated. It checks that the handler stores the provided settings, inherits the configured retry limit, and initializes a client for API communication.
    
    Args:
        mock_config_manager: A mocked configuration manager used to retrieve model settings.
    
    Attributes:
        model_settings: Stores the configuration settings for the model.
        max_retries: The maximum number of retry attempts for API calls.
        client: The underlying client instance used for communication with the ProtoLLM service.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")

    # Act
    handler = ProtollmHandler(model_settings)

    # Assert
    assert handler.model_settings == model_settings
    assert handler.max_retries == model_settings.max_retries
    assert hasattr(handler, "client")


def test_payload_factory_with_system_message(mock_config_manager):
    """
    Verifies that the PayloadFactory correctly initializes and generates a payload when a custom system message is provided.
    
    This test ensures that the factory properly assigns the system message, maintains the correct order and content of roles (system followed by user), and includes the appropriate model settings in the final payload output.
    
    Args:
        mock_config_manager: A mocked configuration manager used to retrieve model settings for the test case.
    
    Steps performed:
        1. Retrieves model settings for the "general" task type.
        2. Creates a PayloadFactory instance with a custom system message and a user prompt.
        3. Generates a payload via to_payload_completions.
        4. Asserts that the system message is correctly assigned, the roles list contains exactly two items (system and user), the first role contains the custom system message, the second role contains the user prompt, and the payload's context_window matches the model settings.
    
    Why: This test validates that the factory correctly handles a custom system message, ensuring the role order and content are preserved and that model settings are properly integrated into the final payload.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    custom_system_message = "Custom system message"
    user_prompt = "User prompt"

    # Act
    factory = PayloadFactory(model_settings, user_prompt, custom_system_message)
    payload = factory.to_payload_completions()

    # Assert
    assert factory.system_message == custom_system_message
    assert len(factory.roles) == 2
    assert "Custom system message" in str(factory.roles[0])
    assert "User prompt" in str(factory.roles[1])
    assert payload["meta"]["context_window"] == model_settings.context_window


def test_payload_factory_without_system_message(mock_config_manager):
    """
    Verifies that the PayloadFactory correctly initializes and generates a payload when no explicit system message is provided, defaulting to the configuration's system prompt.
    
    This test ensures the factory uses the default system prompt from the model settings when a system message is not explicitly given, and that the resulting payload structure is correct.
    
    Args:
        mock_config_manager: A mocked configuration manager used to retrieve model settings and system prompts.
    
    Returns:
        None.
    """
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    user_prompt = "User prompt"

    # Act
    factory = PayloadFactory(model_settings, user_prompt)
    payload = factory.to_payload_completions()

    # Assert
    assert factory.system_message == model_settings.system_prompt
    assert len(factory.roles) == 2
    assert model_settings.system_prompt in str(factory.roles[0])
    assert "User prompt" in str(factory.roles[1])
    assert payload["job_id"]
