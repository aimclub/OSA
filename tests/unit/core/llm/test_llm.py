import logging

import pytest

from osa_tool.core.llm.llm import ModelHandlerFactory, PayloadFactory, ProtollmHandler
from tests.utils.fixtures.models import DummyLLMClient


def test_payload_factory_generates_expected_structure(mock_config_manager):
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
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)

    # Act
    result = handler.send_request("hello world")

    # Assert
    assert result == "sync response"


@pytest.mark.asyncio
async def test_async_request_calls_llm(mock_config_manager, patch_llm_connector, caplog):
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)

    # Act
    with caplog.at_level(logging.DEBUG, logger="rich"):
        result = await handler.async_request("async hello")

    # Assert
    assert result == "async response"
    assert "async hello" in caplog.text
    assert "async response" in caplog.text
    assert "user_tokens=" in caplog.text
    assert "max_output_tokens=" in caplog.text
    assert "Asynchronous LLM response: tokens=" in caplog.text


def test_prepare_messages_rejects_invalid_token_budget(mock_config_manager):
    model_settings = mock_config_manager.get_model_settings("general")
    model_settings.context_window = 100
    model_settings.max_tokens = 100
    handler = ProtollmHandler(model_settings)

    with pytest.raises(ValueError, match="Invalid LLM token budget"):
        handler._prepare_messages("must not disappear", "system")


def test_limit_tokens_returns_short_prompt_without_truncating(mock_config_manager, mocker):
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)
    truncator = mocker.patch("osa_tool.core.llm.llm.truncate_to_tokens")

    result = handler._limit_tokens("short prompt")

    assert result == "short prompt"
    truncator.assert_not_called()


def test_limit_tokens_warns_when_prompt_is_truncated(mock_config_manager, caplog):
    model_settings = mock_config_manager.get_model_settings("general")
    model_settings.context_window = 110
    model_settings.max_tokens = 5
    handler = ProtollmHandler(model_settings)

    with caplog.at_level(logging.WARNING, logger="rich"):
        result = handler._limit_tokens("This prompt contains considerably more than five tokens.")

    assert result != "This prompt contains considerably more than five tokens."
    assert "will be truncated" in caplog.text
    assert "strategy=middle-out" in caplog.text


@pytest.mark.asyncio
async def test_generate_concurrently_orders_results(mock_config_manager, patch_llm_connector):
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
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    model_settings.api = api
    handler = ProtollmHandler(model_settings)

    # Act
    url = handler._build_model_url(model_settings.model)

    # Assert
    assert url.startswith(expected_prefix) or expected_prefix == ""


def test_get_llm_params_filters_none(mock_config_manager, patch_llm_connector):
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")
    handler = ProtollmHandler(model_settings)

    # Act
    params = handler._get_llm_params()

    # Assert
    assert "temperature" in params
    assert all(v is not None for v in params.values())


def test_model_handler_factory_builds_correct_type(mock_config_manager):
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")

    # Act
    handler = ModelHandlerFactory.build(model_settings)

    # Assert
    assert isinstance(handler, ProtollmHandler)


def test_protollm_handler_init(mock_config_manager):
    # Arrange
    model_settings = mock_config_manager.get_model_settings("general")

    # Act
    handler = ProtollmHandler(model_settings)

    # Assert
    assert handler.model_settings == model_settings
    assert handler.max_retries == model_settings.max_retries
    assert hasattr(handler, "client")


def test_payload_factory_with_system_message(mock_config_manager):
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
