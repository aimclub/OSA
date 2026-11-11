import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage, SystemMessage, ToolMessage
from langchain_gigachat import GigaChat
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from osa_tool.core.llm.connectors import (
    GIGACHAT_OAUTH_URL,
    ChatRESTServer,
    _gigachat_access_token,
    create_llm_connector,
)


@pytest.fixture(autouse=True)
def clear_key_env(monkeypatch):
    """Keep provider keys out of the ambient environment for every test here."""
    for name in ("LLM_SERVICE_KEY", "OPENAI_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-fallback")


@pytest.mark.parametrize(
    "api,base_url,expected_type",
    [
        ("openai", "https://api.openai.com/v1", ChatOpenAI),
        ("openai", "https://openrouter.ai/api/v1", ChatOpenAI),
        ("ollama", "http://localhost:11434", ChatOllama),
        ("itmo", "https://self-hosted.example/api/v1", ChatRESTServer),
    ],
)
def test_create_llm_connector_routes_by_api(api, base_url, expected_type):
    # Act
    client = create_llm_connector(api=api, base_url=base_url, model="some-model")

    # Assert
    assert isinstance(client, expected_type)


def test_create_llm_connector_passes_model_name_to_rest_server():
    # Act
    client = create_llm_connector(api="itmo", base_url="https://self-hosted.example", model="custom-model")

    # Assert
    assert client.model_name == "custom-model"


def test_gigachat_host_builds_a_gigachat_client(monkeypatch):
    # Arrange
    monkeypatch.setenv("AUTHORIZATION_KEY", "basic-key")
    monkeypatch.setattr("osa_tool.core.llm.connectors._gigachat_access_token", lambda: "access-token")

    # Act
    client = create_llm_connector(
        api="openai",
        base_url="https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
        model="GigaChat",
    )

    # Assert
    assert isinstance(client, GigaChat)
    assert client.model == "GigaChat"


def test_gigachat_drops_the_openai_only_extra_body(monkeypatch):
    # Arrange
    monkeypatch.setattr("osa_tool.core.llm.connectors._gigachat_access_token", lambda: "access-token")

    # Act
    client = create_llm_connector(
        api="openai",
        base_url="https://gigachat.devices.sberbank.ru/api/v1",
        model="GigaChat",
        temperature=0.05,
        max_tokens=4096,
        top_p=0.95,
        extra_body={"providers": {"only": ["azure"]}},
    )

    # Assert
    assert isinstance(client, GigaChat)
    assert (client.temperature, client.max_tokens, client.top_p) == (0.05, 4096, 0.95)
    assert "extra_body" not in (client.model_extra or {})


def test_gigachat_access_token_requires_the_authorisation_key(monkeypatch):
    # Arrange
    monkeypatch.delenv("AUTHORIZATION_KEY", raising=False)

    # Act & Assert
    with pytest.raises(ValueError, match="AUTHORIZATION_KEY"):
        _gigachat_access_token()


@pytest.mark.parametrize(
    "status,body,expected",
    [
        (401, '{"message": "denied"}', "status code 401"),
        (200, "<html>gateway</html>", "unexpected body"),
        (200, '{"no_token": true}', "unexpected body"),
    ],
)
def test_gigachat_access_token_reports_failed_exchanges(monkeypatch, status, body, expected):
    # Arrange
    class Response:
        def __init__(self):
            self.status_code = status
            self.text = body

    monkeypatch.setenv("AUTHORIZATION_KEY", "basic-key")
    monkeypatch.setattr("osa_tool.core.llm.connectors.requests.post", lambda *a, **kw: Response())

    # Act & Assert
    with pytest.raises(ValueError, match=expected):
        _gigachat_access_token()


def test_gigachat_access_token_posts_the_authorisation_key(monkeypatch):
    # Arrange
    sent = {}

    class Response:
        status_code = 200
        text = '{"access_token": "token-value"}'

    def fake_post(url, headers, data, timeout):
        sent.update(url=url, headers=headers, data=data, timeout=timeout)
        return Response()

    monkeypatch.setenv("AUTHORIZATION_KEY", "basic-key")
    monkeypatch.setattr("osa_tool.core.llm.connectors.requests.post", fake_post)

    # Act
    token = _gigachat_access_token()

    # Assert
    assert token == "token-value"
    assert sent["url"] == GIGACHAT_OAUTH_URL
    assert sent["headers"]["Authorization"] == "Basic basic-key"
    assert sent["data"] == {"scope": "GIGACHAT_API_PERS"}
    assert sent["timeout"] > 0


@pytest.mark.parametrize("base_url", ["https://openrouter.ai/api/v1", "https://api.vsegpt.ru/v1"])
def test_service_hosts_take_the_service_key(monkeypatch, base_url):
    # Arrange
    monkeypatch.setenv("LLM_SERVICE_KEY", "sk-service")
    monkeypatch.setenv("OPENAI_KEY", "sk-openai")

    # Act
    client = create_llm_connector(api="openai", base_url=base_url, model="some-model")

    # Assert
    assert client.openai_api_key.get_secret_value() == "sk-service"


def test_other_hosts_take_the_openai_key(monkeypatch):
    # Arrange
    monkeypatch.setenv("LLM_SERVICE_KEY", "sk-service")
    monkeypatch.setenv("OPENAI_KEY", "sk-openai")

    # Act
    client = create_llm_connector(api="openai", base_url="https://api.openai.com/v1", model="gpt-4o")

    # Assert
    assert client.openai_api_key.get_secret_value() == "sk-openai"


def test_missing_provider_key_falls_back_to_the_documented_variable():
    # Act
    client = create_llm_connector(api="openai", base_url="https://api.openai.com/v1", model="gpt-4o")

    # Assert
    assert client.openai_api_key is None
    assert client.root_client.api_key == "sk-fallback"


def test_rest_server_converts_messages_by_role():
    # Act
    converted = ChatRESTServer._convert_messages(
        [SystemMessage(content="sys"), HumanMessage(content="hi"), AIMessage(content="hello")]
    )

    # Assert
    assert converted == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_rest_server_rejects_non_text_content():
    # Act & Assert
    with pytest.raises(ValueError, match="Must have type 'text'"):
        ChatRESTServer._convert_messages([HumanMessage(content=[{"type": "image"}])])


def test_rest_server_converts_message_subclasses():
    # Act
    converted = ChatRESTServer._convert_messages([AIMessageChunk(content="chunk")])

    # Assert
    assert converted == [{"role": "assistant", "content": "chunk"}]


def test_rest_server_rejects_unsupported_message_type():
    # Act & Assert
    with pytest.raises(ValueError, match="unsupported message type"):
        ChatRESTServer._convert_messages([ToolMessage(content="x", tool_call_id="1")])


@pytest.mark.parametrize(
    "base_url,expected",
    [
        ("https://openrouter.ai/api/v1", "sk-service"),
        ("https://api.vsegpt.ru/v1", "sk-service"),
        ("https://api.vsegpt.io/v1", "sk-service"),
        ("https://api.openai.com/v1", "sk-openai"),
        ("https://openrouter.ai.example.com/v1", "sk-openai"),
        ("https://notopenrouter.ai/v1", "sk-openai"),
    ],
)
def test_service_key_matches_the_host_not_a_substring(monkeypatch, base_url, expected):
    # Arrange
    monkeypatch.setenv("LLM_SERVICE_KEY", "sk-service")
    monkeypatch.setenv("OPENAI_KEY", "sk-openai")

    # Act
    client = create_llm_connector(api="openai", base_url=base_url, model="some-model")

    # Assert
    assert client.openai_api_key.get_secret_value() == expected


def test_openai_params_reach_the_client():
    # Arrange
    extra_body = {"providers": {"only": ["azure"]}}

    # Act
    client = create_llm_connector(
        api="openai",
        base_url="https://openrouter.ai/api/v1",
        model="openai/gpt-4o",
        temperature=0.05,
        max_tokens=4096,
        top_p=0.95,
        extra_body=extra_body,
    )

    # Assert
    assert client.model_name == "openai/gpt-4o"
    assert client.openai_api_base == "https://openrouter.ai/api/v1"
    assert (client.temperature, client.max_tokens, client.top_p) == (0.05, 4096, 0.95)
    assert client.extra_body == extra_body


def test_rest_server_posts_the_expected_envelope(monkeypatch):
    # Arrange
    sent = {}

    class Response:
        status_code = 200
        text = '{"content": "hi there"}'
        encoding = "utf-8"

    def fake_post(url, headers, json, timeout):
        sent.update(url=url, payload=json, timeout=timeout)
        return Response()

    monkeypatch.setattr("osa_tool.core.llm.connectors.requests.post", fake_post)
    client = ChatRESTServer(model_name="m", base_url="https://self-hosted.example")

    # Act
    result = client._generate([SystemMessage(content="sys"), HumanMessage(content="hi")])

    # Assert
    assert sent["url"] == "https://self-hosted.example/chat_completion"
    assert sent["payload"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    assert sent["payload"]["meta"]["tokens_limit"] == client.max_tokens
    assert result.generations[0].message.content == "hi there"
    assert sent["timeout"] > 0


@pytest.mark.parametrize(
    "status,expected",
    [(404, "Maybe you need to connect to the corporate network"), (500, "status code 500")],
)
def test_rest_server_maps_error_statuses(monkeypatch, status, expected):
    # Arrange
    class Response:
        def __init__(self):
            self.status_code = status
            self.text = "boom"
            self.encoding = "utf-8"

    monkeypatch.setattr("osa_tool.core.llm.connectors.requests.post", lambda **kwargs: Response())
    client = ChatRESTServer(base_url="https://self-hosted.example")

    # Act & Assert
    with pytest.raises(ValueError, match=expected):
        client._create_chat([HumanMessage(content="hi")])
