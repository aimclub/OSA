import pytest

from osa_tool.core.llm.llm import ModelHandlerFactory, PayloadFactory, ProtollmHandler
from tests.utils.fixtures.models import DummyLLMClient


def test_payload_factory_generates_expected_structure(mock_config_loader):
    # Arrange
    config = mock_config_loader.config
    factory = PayloadFactory(config, "my test prompt")

    # Act
    payload = factory.to_payload_completions()

    # Assert
    assert set(payload.keys()) == {"job_id", "meta", "messages"}
    assert payload["meta"]["temperature"] == config.llm.temperature
    assert payload["meta"]["tokens_limit"] == config.llm.max_tokens
    assert any("my test prompt" in str(msg) for msg in payload["messages"])


def test_initialize_payload_sets_payload(mock_config_loader):
    # Arrange
    config = mock_config_loader.config
    handler = ProtollmHandler(config)
    handler.client = DummyLLMClient()

    # Act
    handler.initialize_payload(config, "init prompt")

    # Assert
    assert "messages" in handler.payload
    assert any("init prompt" in str(m) for m in handler.payload["messages"])


def test_send_request_calls_llm(monkeypatch, mock_config_loader, patch_llm_connector):
    # Arrange
    config = mock_config_loader.config
    handler = ProtollmHandler(config)

    # Act
    result = handler.send_request("hello world")

    # Assert
    assert result == "sync response"


@pytest.mark.asyncio
async def test_async_request_calls_llm(mock_config_loader, patch_llm_connector):
    # Arrange
    config = mock_config_loader.config
    handler = ProtollmHandler(config)

    # Act
    result = await handler.async_request("async hello")

    # Assert
    assert result == "async response"


@pytest.mark.asyncio
async def test_generate_concurrently_orders_results(mock_config_loader, patch_llm_connector):
    # Arrange
    config = mock_config_loader.config
    handler = ProtollmHandler(config)
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
        ("other", ""),  # fallback to llm.url
    ],
)
def test_build_model_url_varies_with_api(mock_config_loader, patch_llm_connector, api, expected_prefix):
    # Arrange
    config = mock_config_loader.config
    config.llm.api = api
    handler = ProtollmHandler(config)

    # Act
    url = handler._build_model_url()

    # Assert
    assert url.startswith(expected_prefix) or expected_prefix == ""


def test_get_llm_params_filters_none(mock_config_loader, patch_llm_connector):
    # Arrange
    config = mock_config_loader.config
    handler = ProtollmHandler(config)

    # Act
    params = handler._get_llm_params()

    # Assert
    assert "temperature" in params
    assert all(v is not None for v in params.values())


def test_model_handler_factory_builds_correct_type(mock_config_loader, patch_llm_connector):
    # Act
    handler = ModelHandlerFactory.build(mock_config_loader.config)

    # Assert
    assert isinstance(handler, ProtollmHandler)
