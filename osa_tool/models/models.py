import asyncio
import os
import time
from abc import ABC, abstractmethod
from typing import Any
from uuid import uuid4

import dotenv
import tiktoken
from langchain.schema import SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from protollm.connectors import create_llm_connector
from pydantic import ValidationError

from osa_tool.config.settings import ModelSettings
from osa_tool.utils.logger import logger
from osa_tool.utils.response_cleaner import JsonParseError


class ModelHandler(ABC):
    """
    Class: modelHandler
    This class handles the sending of requests to a specified URL and the initialization of payloads for instances.

    Methods:
     send_request: Sends a request to a specified URL and returns the response. The response is of type requests.Response.

     initialize_payload: Initializes the payload for the instance using the provided configuration and prompt.
      The payload is generated using the payloadFactory and is then converted to payload completions and stored in the instance's payload attribute.
      The method takes two arguments: config which are the configuration settings to be used for payload generation,
      and prompt which is the prompt to be used for payload generation. The method does not return anything.
    """

    url: str
    payload: dict

    @abstractmethod
    def send_request(self, prompt: str, system_message: str = None) -> str: ...

    @abstractmethod
    def send_and_parse(self, prompt: str, parser: callable, system_message: str = None, retry_delay: float = 0.5): ...

    @abstractmethod
    async def async_request(self, prompt: str, system_message: str = None) -> str: ...

    @abstractmethod
    async def async_send_and_parse(
        self,
        prompt: str,
        parser: callable,
        system_message: str = None,
        retry_delay: float = 0.5,
    ): ...

    @abstractmethod
    async def generate_concurrently(self, prompts: list[str], system_message: str = None) -> list: ...

    @abstractmethod
    def run_chain(
        self, prompt: str, parser: PydanticOutputParser, system_message: str = None, retry_delay: float = 0.5
    ) -> Any: ...

    @abstractmethod
    async def async_run_chain(
        self, prompt: str, parser: PydanticOutputParser, system_message: str = None, retry_delay: float = 0.5
    ) -> Any: ...

    def initialize_payload(self, model_settings: ModelSettings, prompt: str, system_message: str = None) -> None:
        """
        Initializes the payload for the instance.

        This method uses the provided configuration and prompt to generate a payload using the payloadFactory.
        The generated payload is then converted to payload completions and stored in the instance's payload attribute.

        Args:
            model_settings: The model settings to use for payload generation.
            system_message: The system message to be used for payload generation.
            prompt: The prompt to be used for payload generation.

        Returns:
            None
        """
        self.payload = PayloadFactory(
            model_settings=model_settings, prompt=prompt, system_message=system_message
        ).to_payload_completions()


class PayloadFactory:
    """
    Class: payloadFactory

    This class is responsible for creating payloads from instance variables. It is initialized with a unique job ID, temperature, tokens limit, prompt, and roles. The payloads can be used for serialization or for sending the instance data over a network.

    Methods:
     __init__:
        Initializes the instance with a unique job ID, temperature, tokens limit, prompt, and roles. The 'config' parameter should include 'llm' with 'temperature' and 'tokens' attributes. The 'prompt' parameter is the initial user prompt.

     to_payload_completions:
        Converts the instance variables to a dictionary payload for completions. This method returns a dictionary with keys 'job_id', 'meta', and 'messages'. The 'meta' key contains a nested dictionary with keys 'temperature' and 'tokens_limit'. The values for these keys are taken from the instance variables of the same names.
    """

    def __init__(self, model_settings: ModelSettings, prompt: str, system_message: str = None):
        """
        Initializes the instance with a unique job ID, temperature, tokens limit, prompt, and roles.

        Args:
            model_settings: The model settings for the instance.
            prompt: The initial user prompt.

        Returns:
            None
        """
        self.job_id = str(uuid4())
        self.temperature = model_settings.temperature
        self.tokens_limit = model_settings.max_tokens
        self.context_window = model_settings.context_window
        self.system_message = system_message or model_settings.system_prompt
        self.prompt = prompt
        self.roles = [
            SystemMessage(content=self.system_message),
            {"role": "user", "content": self.prompt},
        ]

    def to_payload_completions(self) -> dict:
        """
        Converts the instance variables to a dictionary payload for completions.

        This method takes no arguments other than the implicit 'self' and returns a dictionary
        with keys 'job_id', 'meta', and 'messages'. The 'meta' key contains a nested dictionary
        with keys 'temperature' and 'tokens_limit'. The values for these keys are taken from
        the instance variables of the same names.

        Returns:
            dict: A dictionary containing the 'job_id', 'meta', and 'messages' from the instance.
        """
        return {
            "job_id": self.job_id,
            "meta": {
                "temperature": self.temperature,
                "tokens_limit": self.tokens_limit,
                "context_window": self.context_window,
            },
            "messages": self.roles,
        }


class ProtollmHandler(ModelHandler):
    """
    This class is designed to handle interactions with the different LLMs using ProtoLLM connector.
    It is initialized with configuration settings and can send requests to the API.

    Methods:
        __init__:
            Initializes the instance with the provided configuration settings.
            This method sets up the instance by assigning the provided configuration settings
            to the instance's config attribute.
            It also retrieves the API from the configuration settings and passes it to the _configure_api method.

        send_request:
            Sends a request and initializes the payload with the given prompt.
            This method sends a request, initializes the payload with the given prompt, and creates a chat completion
            with the specified model, messages, max tokens, and temperature from the configuration.
            It then returns the content of the first choice from the response.

        _configure_api:
            Configures the API for the instance based on the provided API name.
            This method loads environment variables, sets the URL and API key based on the provided API name,
            and initializes the ProtoLLM connector with the set URL and API key.
    """

    def __init__(self, model_settings: ModelSettings):
        """
        Initializes the instance with the provided configuration settings.
        This method sets up the instance by assigning the provided configuration settings to the instance's config attribute.
        It also retrieves the API from the configuration settings and passes it to the _configure_api method.
        Args:
            model_settings: The model settings to use for this handler.
        Returns:
            None
        """
        self.model_settings = model_settings
        self.max_retries = model_settings.max_retries
        self._configure_api(model_settings.api, model_name=model_settings.model)

    def send_request(self, prompt: str, system_message: str = None) -> str:
        """
        Sends a request to a specified URL with a payload initialized with a given prompt.

        This method initializes a payload with the provided prompt and configuration,
        sends a POST request to a specified URL with this payload, and logs the response.

        Args:
            prompt (str): The prompt to initialize the payload with.
            system_message (str, optional): The system message to initialize the payload with.

        Returns:
            str: The response received from the request.
        """
        safe_prompt = self._limit_tokens(prompt)
        self.initialize_payload(self.model_settings, safe_prompt, system_message)
        messages = self.payload["messages"]
        response = self.client.invoke(messages)
        return response.content

    def send_and_parse(self, prompt: str, parser: callable, system_message: str = None, retry_delay: float = 0.5):
        """
        Sends a prompt to the LLM, applies a parser to the response, and retries on parsing or validation errors.

        This method attempts to send the request up to `self.max_retries` times.
        If the parser raises `JsonParseError` or `pydantic.ValidationError`,
        the request is retried with a delay. If all attempts fail, the last raw
        LLM response is logged at DEBUG level and the last exception is raised.

        Args:
            prompt (str): The prompt to send to the LLM.
            parser (callable): A function that parses and validates the raw LLM response.
            system_message (str, optional): The system message to initialize the payload with.
            retry_delay (float, optional): Delay in seconds between retry attempts. Defaults to 0.5.

        Returns:
            Any: The successfully parsed result from the parser.

        Raises:
            JsonParseError: If JSON parsing fails after all retries.
            ValidationError: If pydantic validation fails after all retries.
        """
        last_error = None
        last_raw = None

        for attempt in range(1, self.max_retries + 1):
            last_raw = self.send_request(prompt, system_message)

            try:
                result = parser(last_raw)

                logger.info(f"Send and parse request success on attempt {attempt}/{self.max_retries}.")
                return result
            except (JsonParseError, ValidationError) as e:
                last_error = e
                logger.warning(f"Parse failed (attempt {attempt}/{self.max_retries}): {e}")

                if attempt < self.max_retries:
                    time.sleep(retry_delay)

        logger.debug("Final failed LLM response after retries:\n%s", last_raw)
        logger.debug(repr(last_error))
        raise

    async def async_request(self, prompt: str, system_message: str = None) -> str:
        """
        Asynchronous alternative of send_request method.
        This method do the same things in general.

        Args:
            prompt (str): The prompt to initialize the payload with.
            system_message (str, optional): The system message to initialize the payload with.

        Returns:
            str: The response received from the request.
        """
        safe_prompt = self._limit_tokens(prompt)
        self.initialize_payload(self.model_settings, safe_prompt, system_message)
        response = await self.client.ainvoke(self.payload["messages"])
        return response.content

    async def async_send_and_parse(
        self,
        prompt: str,
        parser: callable,
        system_message: str = None,
        retry_delay: float = 0.5,
    ):
        """
        Asynchronously sends a prompt to the LLM, applies a parser to the response,
        and retries on parsing errors.

        This method attempts to send the request up to `self.max_retries` times.
        If the parser raises `JsonParseError` or `pydantic.ValidationError`,
        the request is retried with a delay. If all attempts fail, the last raw
        LLM response is logged at DEBUG level and the last exception is raised.

        Args:
            prompt (str): The prompt to send to the LLM.
            parser (callable): A function that parses and validates the raw LLM response.
            system_message (str, optional): The system message to initialize the payload with.
            retry_delay (float, optional): Delay in seconds between retry attempts. Defaults to 0.5.

        Returns:
            Any: The successfully parsed result from the parser.

        Raises:
            JsonParseError: If JSON parsing fails after all retries.
            ValidationError: If pydantic validation fails after all retries.
        """
        last_error = None
        last_raw = None

        for attempt in range(1, self.max_retries + 1):
            last_raw = await self.async_request(prompt, system_message)

            try:
                result = parser(last_raw)

                logger.info(f"Async send and parse request success on attempt {attempt}/{self.max_retries}.")
                return result

            except JsonParseError as e:
                last_error = e
                logger.warning(f"Async parse failed (attempt {attempt}/{self.max_retries}): {e}")

                if attempt < self.max_retries:
                    await asyncio.sleep(retry_delay)

        logger.debug("Final failed async LLM response after retries:\n%s", last_raw)
        logger.debug(repr(last_error))
        raise

    async def generate_concurrently(self, prompts: list[str], system_message: str = None) -> list[str]:
        """
        Sends a batch of requests to the specified llm server endpoint.
        Requests would be sent in concurrent format and processed in the order of their input.

        Args:
            prompts: The batch of prompts to send on llm server endpoint.
            system_message (str, optional): The system message to initialize the payload with.

        Returns:
            list[str]: The list of responses from awaited coroutines.
        """
        coroutines = [self.async_request(p, system_message) for p in prompts]
        return await asyncio.gather(*coroutines)

    def run_chain(
        self, prompt: str, parser: PydanticOutputParser, system_message: str = None, retry_delay: float = 0.5
    ) -> Any:
        """
        Runs a structured LLM chain synchronously, parses the output, and retries on errors.

        The chain follows the sequence:
            prompt → system prompt → LLM → parser → validated object

        Args:
            prompt (str): The user input prompt to send to the LLM.
            parser (PydanticOutputParser): The parser used to validate and transform the LLM output.
            system_message (str, optional): Optional system message to provide context to the LLM.
            retry_delay (float, optional): Delay in seconds between retry attempts. Defaults to 0.5.

        Returns:
            Any: The successfully parsed object returned by the parser.

        Raises:
            Exception: The last exception encountered if all retry attempts fail.
        """
        chain = (
            ChatPromptTemplate.from_messages(
                [("system", system_message or self.model_settings.system_prompt), ("user", "{input}")]
            )
            | self.client
            | parser
        )

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = chain.invoke({"input": prompt})

                logger.info(
                    f"Run chain success on attempt {attempt}/{self.max_retries}. " f"Parser={parser.__class__.__name__}"
                )
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Run chain failed (attempt {attempt}/{self.max_retries}): {e}")

                if attempt < self.max_retries:
                    time.sleep(retry_delay)

        logger.debug(repr(last_error))
        raise

    async def async_run_chain(
        self, prompt: str, parser: PydanticOutputParser, system_message: str = None, retry_delay: float = 0.5
    ) -> Any:
        """
        Runs a structured LLM chain asynchronously, parses the output, and retries on errors.

        The chain follows the sequence:
            prompt → system prompt → LLM → parser → validated object

        Args:
            prompt (str): The user input prompt to send to the LLM.
            parser (PydanticOutputParser): The parser used to validate and transform the LLM output.
            system_message (str, optional): Optional system message to provide context to the LLM.
            retry_delay (float, optional): Delay in seconds between retry attempts. Defaults to 0.5.

        Returns:
            Any: The successfully parsed object returned by the parser.

        Raises:
            Exception: The last exception encountered if all retry attempts fail.
        """
        chain = (
            ChatPromptTemplate.from_messages(
                [("system", system_message or self.model_settings.system_prompt), ("user", "{input}")]
            )
            | self.client
            | parser
        )

        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = await chain.ainvoke({"input": prompt})

                logger.info(
                    f"Async chain success on attempt {attempt}/{self.max_retries}. "
                    f"Parser={parser.__class__.__name__}"
                )
                return result

            except Exception as e:
                last_error = e
                logger.warning(f"Async run_chain failed (attempt {attempt}/{self.max_retries}): {e}")

                if attempt < self.max_retries:
                    await asyncio.sleep(retry_delay)

        logger.debug(repr(last_error))
        raise

    def _build_model_url(self) -> str:
        """Builds the model URL based on the LLM API type."""
        url_templates = {
            "itmo": f"self_hosted;{os.getenv('ITMO_MODEL_URL', self.model_settings.base_url)};{self.model_settings.model}",
            "ollama": f"ollama;{self.model_settings.localhost};{self.model_settings.model}",
        }
        return url_templates.get(self.model_settings.api, f"{self.model_settings.base_url};{self.model_settings.model}")

    def _get_llm_params(self):
        """Extract LLM parameters from config"""
        llm_params = ["temperature", "max_tokens", "top_p"]

        return {
            name: getattr(self.model_settings, name)
            for name in llm_params
            if getattr(self.model_settings, name, None) is not None
        }

    def _configure_api(self, api: str, model_name: str) -> None:
        """
        Configures the API for the instance based on the provided API name.

        This method loads environment variables, sets the URL and API key based on the provided API name,
        and initializes the OpenAI client with the set URL and API key.

        Args:
            api: The name of the API to configure. It can be either "openai" or "vsegpt".

        Returns:
            None
        """
        dotenv.load_dotenv()

        self.client = create_llm_connector(
            model_url=self._build_model_url(),
            extra_body={"providers": {"only": self.model_settings.allowed_providers}},
            **self._get_llm_params(),
        )

    def _limit_tokens(self, text: str, safety_buffer: int = 100, mode: str = "middle-out") -> str:
        """
        Limits text to fit within the model's context window.

        Calculates: Available Input = Total Context - Max Output - Safety Buffer
        """
        model_context_limit = getattr(self.model_settings, "context_window")
        max_output_tokens = self.model_settings.max_tokens
        encoding_name = self.model_settings.encoder

        max_input_tokens = model_context_limit - max_output_tokens - safety_buffer

        try:
            encoding = tiktoken.get_encoding(encoding_name)
        except ValueError:
            encoding = tiktoken.get_encoding("cl100k_base")

        tokens = encoding.encode(text)

        if len(tokens) <= max_input_tokens:
            return text

        if mode == "start":
            truncated_tokens = tokens[:max_input_tokens]
        elif mode == "end":
            truncated_tokens = tokens[-max_input_tokens:]
        elif mode == "middle-out":
            half_limit = max_input_tokens // 2
            truncated_tokens = tokens[:half_limit] + tokens[-half_limit:]
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return encoding.decode(truncated_tokens)


class ModelHandlerFactory:
    """
    Class: modelHandlerFactory

    This class is responsible for creating handlers based on the configuration of the class. It supports the creation of handlers for different types of models.

    Methods:
     build:
        Builds and returns a model handler instance based on the given configuration.
    """

    @classmethod
    def build(cls, model_settings: ModelSettings) -> ProtollmHandler:
        """
        Builds and returns a handler based on the configuration of the class.

        This method retrieves the configuration from the class
        and then creates and returns a handler using the configuration.

        Args:
            model_settings: The model settings to use for the handler.
            cls: The class from which the configuration is retrieved.

        Returns:
            ModelHandler: An instance of the appropriate model handler.
        """
        return ProtollmHandler(model_settings)
