import json
import os
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

import requests
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_gigachat import GigaChat
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

GIGACHAT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"

_OAUTH_TIMEOUT = 30
_COMPLETION_TIMEOUT = 300


class ChatRESTServer(BaseChatModel):
    """
    Chat model for the self-hosted REST endpoint used by `--api itmo`.

    The endpoint expects a job envelope rather than an OpenAI-compatible body,
    so it cannot be served by ChatOpenAI.
    """

    model_name: str | None = "llama"
    base_url: str = "http://localhost"
    max_tokens: int = 2048
    temperature: float = 0.1

    @property
    def _llm_type(self) -> str:
        return "chat-rest-server"

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"model_name": self.model_name, "url": self.base_url}

    @staticmethod
    def _convert_messages(messages: list[BaseMessage]) -> list[dict[str, str]]:
        """
        Converts LangChain messages into the role/content pairs the endpoint expects.

        Roles are matched by isinstance so that subclasses such as AIMessageChunk
        still convert.

        Args:
            messages: The messages to convert.

        Returns:
            list[dict[str, str]]: The converted messages.

        Raises:
            ValueError: If a message has an unsupported type or non-text content.
        """
        roles = ((SystemMessage, "system"), (HumanMessage, "user"), (AIMessage, "assistant"))
        converted = []
        for message in messages:
            role = next((name for kind, name in roles if isinstance(message, kind)), None)
            if role is None:
                raise ValueError(f"Received unsupported message type: {type(message).__name__}.")
            if not isinstance(message.content, str):
                raise ValueError("Unsupported message content type. Must have type 'text'.")
            converted.append({"role": role, "content": message.content})
        return converted

    def _create_chat(self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
        """
        Posts one completion request to the REST endpoint.

        Args:
            messages: The conversation to send.
            stop: Optional stop words.
            **kwargs: Extra fields merged into the request payload.

        Returns:
            dict[str, Any]: The decoded response body.

        Raises:
            ValueError: If the endpoint answers with anything but 200.
        """
        payload = {
            "job_id": str(uuid4()),
            "priority": None,
            "source": "local",
            "meta": {
                "temperature": self.temperature,
                "tokens_limit": self.max_tokens,
                "stop_words": stop,
                "model": None,
            },
            "messages": self._convert_messages(messages),
            **kwargs,
        }

        response = requests.post(
            url=f"{self.base_url}/chat_completion",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=_COMPLETION_TIMEOUT,
        )
        response.encoding = "utf-8"
        if response.status_code == 404:
            raise ValueError(
                "Self-hosted LLM call failed with status code 404. "
                "Maybe you need to connect to the corporate network."
            )
        if response.status_code != 200:
            raise ValueError(
                f"Self-hosted LLM call failed with status code {response.status_code}. Details: {response.text}"
            )
        return json.loads(response.text)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        response = self._create_chat(messages, stop, **kwargs)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response["content"]))])


def _gigachat_access_token() -> str:
    """
    Exchanges the configured authorisation key for a GigaChat access token.

    The token is valid for thirty minutes, so it is fetched per connector.

    Returns:
        str: The access token.

    Raises:
        ValueError: If AUTHORIZATION_KEY is unset or the exchange fails.
    """
    authorization_key = os.getenv("AUTHORIZATION_KEY")
    if not authorization_key:
        raise ValueError("GigaChat requires an authorisation key. Set AUTHORIZATION_KEY in the environment.")

    response = requests.post(
        GIGACHAT_OAUTH_URL,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid4()),
            "Authorization": f"Basic {authorization_key}",
        },
        data={"scope": "GIGACHAT_API_PERS"},
        timeout=_OAUTH_TIMEOUT,
    )
    if response.status_code != 200:
        raise ValueError(
            f"GigaChat token exchange failed with status code {response.status_code}. Details: {response.text}"
        )
    try:
        return json.loads(response.text)["access_token"]
    except (json.JSONDecodeError, KeyError) as error:
        raise ValueError(f"GigaChat token exchange returned an unexpected body: {response.text}") from error


def _resolve_api_key(hostname: str) -> str | None:
    """
    Returns the explicitly configured key for a provider, if there is one.

    OpenRouter and VseGPT read LLM_SERVICE_KEY, every other host reads OPENAI_KEY.
    None is a meaningful result: the OpenAI SDK then falls back to OPENAI_API_KEY,
    the variable OSA documents.

    Args:
        hostname: The host part of the provider base URL.

    Returns:
        str | None: The configured key, or None to let the SDK resolve it.
    """
    labels = hostname.split(".")
    if hostname == "openrouter.ai" or hostname.endswith(".openrouter.ai") or "vsegpt" in labels:
        return os.getenv("LLM_SERVICE_KEY")
    return os.getenv("OPENAI_KEY")


def create_llm_connector(api: str, base_url: str, model: str, **params: Any) -> BaseChatModel:
    """
    Builds the LangChain chat model for the configured provider.

    Ollama and the self-hosted endpoint are selected by `api`; the remaining
    providers are told apart by their host. For GigaChat the host only selects
    the provider: its client carries its own endpoint and ignores `base_url`.

    Args:
        api: The provider selected through `--api`.
        base_url: The resolved endpoint for that provider.
        model: The model name to request.
        **params: Sampling and request parameters passed to the chat model.

    Returns:
        BaseChatModel: A chat model ready to invoke.
    """
    if api == "ollama":
        return ChatOllama(model=model, base_url=base_url, **params)
    if api == "itmo":
        return ChatRESTServer(model_name=model, base_url=base_url, **params)

    hostname = urlparse(base_url).hostname or ""
    if "gigachat" in hostname.split("."):
        params.pop("extra_body", None)
        return GigaChat(model=model, access_token=_gigachat_access_token(), **params)
    return ChatOpenAI(model=model, base_url=base_url, api_key=_resolve_api_key(hostname), **params)
