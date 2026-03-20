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
    Class for managing HTTP request operations and payload configuration to interact with external endpoints.
    
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
    def send_request(self, prompt: str, system_message: str = None, retry_delay: float = 1) -> str: ...

    @abstractmethod
    def send_and_parse(self, prompt: str, parser: callable, system_message: str = None, retry_delay: float = 0.5): ...

    @abstractmethod
    async def async_request(self, prompt: str, system_message: str = None, retry_delay: float = 1) -> str: ...

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
        
        This method uses the provided model settings, prompt, and optional system message to generate a payload via the PayloadFactory. The resulting payload is converted into a completions-ready dictionary and stored in the instance's `payload` attribute. This prepares the data for subsequent API calls or processing steps.
        
        Args:
            model_settings: Configuration containing model-specific parameters (e.g., temperature, tokens_limit) for payload generation.
            prompt: The user input or instruction to be processed.
            system_message: An optional system-level instruction or context to guide the model's behavior. Defaults to None.
        
        Returns:
            None
        """
        self.payload = PayloadFactory(
            model_settings=model_settings, prompt=prompt, system_message=system_message
        ).to_payload_completions()


class PayloadFactory:
    """
    The `PayloadFactory` class is responsible for constructing and managing the structured data payloads used throughout the repository analysis and enhancement pipeline. It standardizes the format and content of data exchanged between different system components, ensuring consistency and reliability in operations such as documentation generation, validation, and repository structuring.
    
        This class is responsible for creating payloads from instance variables. It is initialized with a unique job ID, temperature, tokens limit, prompt, and roles. The payloads can be used for serialization or for sending the instance data over a network.
    
        Methods:
         __init__:
            Initializes the instance with a unique job ID, temperature, tokens limit, prompt, and roles. The 'config' parameter should include 'llm' with 'temperature' and 'tokens' attributes. The 'prompt' parameter is the initial user prompt.
    
         to_payload_completions:
            Converts the instance variables to a dictionary payload for completions. This method returns a dictionary with keys 'job_id', 'meta', and 'messages'. The 'meta' key contains a nested dictionary with keys 'temperature' and 'tokens_limit'. The values for these keys are taken from the instance variables of the same names.
    """


    def __init__(self, model_settings: ModelSettings, prompt: str, system_message: str = None):
        """
        Initializes a PayloadFactory instance with configuration for generating structured payloads.
        
        Args:
            model_settings: Contains model-specific parameters such as temperature, token limits, and context window.
            prompt: The initial user input or query to be processed.
            system_message: An optional custom system message; if not provided, defaults to the system prompt from model_settings.
        
        Why:
        - A unique job ID is generated to track and identify each payload instance uniquely.
        - Model parameters (temperature, token limits, context window) are extracted from model_settings to configure the generation behavior.
        - The system message sets the assistant's behavior; using a custom one allows overriding the default prompt.
        - The roles list structures the conversation with a system message followed by the user prompt, preparing the payload for API consumption.
        
        Note:
        This method does not return a value; it initializes the instance attributes.
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
        
        This method constructs a payload dictionary suitable for a completions API call. It organizes the instance's data into the required structure, which includes a job identifier, metadata about the generation parameters, and the conversation messages.
        
        Args:
            job_id: The identifier for the job or task.
            temperature: The sampling temperature controlling randomness in generation.
            tokens_limit: The maximum number of tokens allowed in the generated output.
            context_window: The size of the context window available for the model.
            roles: The list of conversation messages, typically structured with roles (e.g., 'user', 'assistant').
        
        Returns:
            dict: A dictionary with keys 'job_id', 'meta', and 'messages'.
                - 'job_id': The job identifier.
                - 'meta': A nested dictionary containing 'temperature', 'tokens_limit', and 'context_window'.
                - 'messages': The list of conversation messages.
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
    The `ProtollmHandler` class manages communication with various large language models via the ProtoLLM connector. It is configured with specific settings and facilitates sending requests to the API.
    
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
        Initializes the ProtollmHandler instance with the provided model settings.
        
        This method sets up the handler by storing the model settings and extracting key configuration values:
        - The model name is saved as the original primary model for reference.
        - The maximum number of retries for API calls is stored.
        The API client is then configured internally using the model name.
        
        Args:
            model_settings: The model settings containing configuration such as the model name and retry limit.
        
        Returns:
            None
        """
        self.model_settings = model_settings
        self._original_primary_model = model_settings.model
        self.max_retries = model_settings.max_retries
        self._configure_api(model_name=model_settings.model)

    def reset_to_primary_model(self) -> None:
        """
        Explicitly restore primary model configuration.
        
        This method resets the current model to the primary model originally configured for the handler.
        It is typically called to revert any temporary model changes, ensuring subsequent API requests use the primary model.
        
        Args:
            None
        
        Returns:
            None
        """
        primary = self._original_primary_model
        if self.model_settings.model != primary:
            logger.info(f"Resetting model from `{self.model_settings.model}` to `{primary}`")
            self._configure_api(model_name=primary)
            self.model_settings.model = primary

    def _iter_configured_models(self):
        """
        Generator that yields each model to attempt in sequence, handling fallback configuration and logging automatically.
        
        This method iterates through the primary model and any configured fallback models. For each model after the first (i.e., during a fallback), it logs a warning about the failure and reconfigures the internal API client to use the new model. This enables transparent retry logic with different models without requiring external intervention.
        
        Args:
            None
        
        Yields:
            model: The name of the model to attempt in the current iteration.
        """
        models_to_try = [self.model_settings.model, *self.model_settings.fallback_models]

        for model_idx, model in enumerate(models_to_try):
            if model_idx > 0:
                logger.warning(
                    f"Model '{self.model_settings.model}' failed. Falling back to model '{model}' ({model_idx + 1}/{len(models_to_try)})"
                )
                self._configure_api(model_name=model)
                self.model_settings.model = model

            yield model

    def _prepare_messages(self, prompt: str, system_message: str) -> list:
        """
        Shared logic to prepare the payload and extract messages.
        
        This method handles the common steps for constructing a request payload and retrieving the formatted messages list. It ensures the prompt fits within the model's token limits, initializes the full payload using the model settings and system message, and then returns the messages portion ready for use in an API call or further processing.
        
        Args:
            prompt: The user input or instruction to be processed.
            system_message: An optional system-level instruction or context to guide the model's behavior.
        
        Returns:
            A list containing the formatted messages, typically including system and user roles, extracted from the initialized payload.
        """
        safe_prompt = self._limit_tokens(prompt)
        self.initialize_payload(self.model_settings, safe_prompt, system_message)
        return self.payload["messages"]

    def send_request(self, prompt: str, system_message: str = None, retry_delay: float = 1) -> str:
        """
        Sends a request using primary model, falling back to alternatives on failure.
        
        SIDE EFFECT: On fallback success, updates `self.model_settings.model`
        to the working fallback model. Does NOT automatically restore primary model.
        
        Attempts the primary model first (without reconfiguration). If it fails,
        sequentially tries models from `model_settings.fallback_models` until
        successful or all options are exhausted. A delay is introduced between retries
        to avoid overwhelming the API or to handle transient errors.
        
        Args:
            prompt: User prompt text.
            system_message: Optional system message to include in the payload.
            retry_delay: Delay in seconds between retry attempts after a failure.
                         This helps mitigate transient issues like rate limits or temporary service unavailability.
        
        Returns:
            Model response content as string.
        
        Raises:
            Exception: The last exception encountered after exhausting all models.
        """
        last_error = None

        for _ in self._iter_configured_models():
            try:
                messages = self._prepare_messages(prompt, system_message)
                response = self.client.invoke(messages)
                return response.content
            except Exception as e:
                last_error = e
                logger.debug(repr(e))
                time.sleep(retry_delay)

        logger.error(f"All models failed. Last error: {last_error}")
        raise last_error

    def send_and_parse(self, prompt: str, parser: callable, system_message: str = None, retry_delay: float = 0.5):
        """
        Sends a prompt to the LLM, applies a parser to the response, and retries on parsing or validation errors.
        
        This method attempts to send the request up to `self.max_retries` times.
        If the parser raises `JsonParseError` or `pydantic.ValidationError`,
        the request is retried with a delay. If all attempts fail, the last raw
        LLM response is logged at DEBUG level and the last exception is raised.
        
        WHY: Retrying on parsing/validation errors allows the LLM another chance to produce a well‑formed response, which is useful when the LLM occasionally outputs malformed JSON or data that does not match the expected schema.
        
        Args:
            prompt: The prompt to send to the LLM.
            parser: A function that parses and validates the raw LLM response. It should raise `JsonParseError` or `pydantic.ValidationError` on failure.
            system_message: Optional system message to initialize the payload with. If provided, it is passed to the underlying `send_request` method.
            retry_delay: Delay in seconds between retry attempts. Defaults to 0.5.
        
        Returns:
            The successfully parsed result from the parser.
        
        Raises:
            JsonParseError: If JSON parsing fails after all retries.
            ValidationError: If pydantic validation fails after all retries.
            Exception: Any exception raised by `send_request` after exhausting all fallback models (if configured) is propagated immediately without retry.
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

    async def async_request(self, prompt: str, system_message: str = None, retry_delay: float = 1) -> str:
        """
        Asynchronous alternative of send_request method.
        Sends an async request using primary model, falling back to alternatives on failure.
        
        SIDE EFFECT: On fallback success, updates `self.model_settings.model`
        to the working fallback model. Does NOT automatically restore primary model.
        
        Attempts the primary model first (without reconfiguration). If it fails,
        sequentially tries models from `model_settings.fallback_models` until
        successful or all options are exhausted. Between each attempt, a delay is introduced to respect rate limits or allow transient issues to resolve.
        
        Args:
            prompt: User prompt text.
            system_message: Optional system message to include in the payload.
            retry_delay: Delay in seconds between retry attempts after a model fails. This helps avoid overwhelming APIs or mitigates transient errors.
        
        Returns:
            Model response content as string.
        
        Raises:
            Exception: The last exception encountered after exhausting all models.
        """
        last_error = None

        for _ in self._iter_configured_models():
            try:
                messages = self._prepare_messages(prompt, system_message)
                response = await self.client.ainvoke(messages)
                return response.content
            except Exception as e:
                last_error = e
                logger.debug(repr(e))
                await asyncio.sleep(retry_delay)

        logger.error(f"All models failed. Last error: {last_error}")
        raise last_error

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
        
        WHY retry: Parsing errors may stem from malformed or unexpected LLM responses.
        Retrying allows the LLM to generate a new, potentially correct response,
        especially after switching back to the primary model (via `reset_to_primary_model`)
        when a fallback model was used due to a prior request failure.
        
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
                self.reset_to_primary_model()

                if attempt < self.max_retries:
                    await asyncio.sleep(retry_delay)

        logger.debug("Final failed async LLM response after retries:\n%s", last_raw)
        logger.debug(repr(last_error))
        raise

    async def generate_concurrently(self, prompts: list[str], system_message: str = None) -> list[str]:
        """
        Sends a batch of requests to the specified LLM server endpoint concurrently.
        Requests are dispatched simultaneously but responses are returned in the same order as the input prompts.
        
        Args:
            prompts: The batch of prompts to send to the LLM server endpoint.
            system_message: Optional system message to initialize the payload with for all requests in the batch.
        
        Returns:
            list[str]: The list of responses from awaited coroutines, maintaining the order of the input prompts.
        
        Why:
            This method enables efficient batch processing by leveraging asynchronous concurrency, reducing overall latency compared to sequential requests. It relies on `async_request` internally, which attempts the primary model and falls back to alternatives if failures occur.
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
        
        WHY: This method provides a robust, synchronous interface for executing a LangChain pipeline with built-in error handling and retries, ensuring reliable structured output from the LLM.
        
        Args:
            prompt: The user input prompt to send to the LLM.
            parser: The parser used to validate and transform the LLM output.
            system_message: Optional system message to provide context to the LLM. If not provided, the handler's default system prompt from model_settings is used.
            retry_delay: Delay in seconds between retry attempts.
        
        Returns:
            The successfully parsed object returned by the parser.
        
        Raises:
            Exception: The last exception encountered if all retry attempts fail. The number of retry attempts is determined by the handler's max_retries attribute.
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
        
        The method retries up to `self.max_retries` times on failure, with a delay between attempts, to improve reliability when the LLM output does not initially satisfy the parser's validation.
        
        Args:
            prompt: The user input prompt to send to the LLM.
            parser: The parser used to validate and transform the LLM output.
            system_message: Optional system message to provide context to the LLM. If not provided, the handler's default system prompt (`self.model_settings.system_prompt`) is used.
            retry_delay: Delay in seconds between retry attempts. Defaults to 0.5.
        
        Returns:
            The successfully parsed object returned by the parser.
        
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

    def _build_model_url(self, model_name: str) -> str:
        """
        Builds the model URL based on the LLM API type.
        
        The method constructs a formatted string that combines API-specific information with the model name. This URL is used to identify and route requests to the appropriate LLM service, whether it's a self-hosted instance, a local Ollama server, or a generic base URL.
        
        Args:
            model_name: The name of the LLM model to be included in the URL.
        
        Returns:
            A formatted string representing the model URL. The format depends on the configured API type:
                - For "itmo": uses a self-hosted template incorporating an environment variable or a fallback base URL.
                - For "ollama": uses a localhost template.
                - For other API types: defaults to combining the base URL with the model name.
        """
        url_templates = {
            "itmo": f"self_hosted;{os.getenv('ITMO_MODEL_URL', self.model_settings.base_url)};{model_name}",
            "ollama": f"ollama;{self.model_settings.localhost};{model_name}",
        }
        return url_templates.get(self.model_settings.api, f"{self.model_settings.base_url};{model_name}")

    def _get_llm_params(self):
        """
        Extract LLM parameters from the model configuration.
        
        This method retrieves a specific subset of LLM (Large Language Model) generation
        parameters—temperature, max_tokens, and top_p—from the handler's model settings.
        It only includes parameters that are explicitly set (i.e., not None) in the
        configuration. This selective extraction ensures that only defined parameters
        are passed downstream, preventing unintended overrides with default or null values.
        
        Returns:
            A dictionary mapping each defined parameter name to its value from the
            model settings. Only parameters that are present and non‑None are included.
        """
        llm_params = ["temperature", "max_tokens", "top_p"]

        return {
            name: getattr(self.model_settings, name)
            for name in llm_params
            if getattr(self.model_settings, name, None) is not None
        }

    def _configure_api(self, model_name: str) -> None:
        """
        Configures the API for the instance based on the provided model name.
        
        This method loads environment variables from a .env file, constructs a model-specific URL,
        and initializes an LLM connector client with the URL, provider restrictions, and additional parameters.
        It is called internally to set up the client connection before making any API requests.
        
        Args:
            model_name: The name of the model used to build the endpoint URL.
        
        Returns:
            None
        """
        dotenv.load_dotenv()

        self.client = create_llm_connector(
            model_url=self._build_model_url(model_name),
            extra_body={"providers": {"only": self.model_settings.allowed_providers}},
            **self._get_llm_params(),
        )

    def _limit_tokens(self, text: str, safety_buffer: int = 100, mode: str = "middle-out") -> str:
        """
        Limits text to fit within the model's context window by truncating tokenized text as needed.
        
        The method calculates the maximum allowable input tokens based on the model's total context window,
        subtracting the maximum output tokens and a safety buffer to prevent overflow. It then tokenizes
        the input text and truncates it according to the specified mode if the token count exceeds the limit.
        
        Args:
            text: The input text string to be limited.
            safety_buffer: Additional tokens reserved as a safety margin to avoid exceeding the context window.
            mode: Determines which part of the text is preserved when truncation is required.
                - "start": Keeps the beginning of the text.
                - "end": Keeps the end of the text.
                - "middle-out": Keeps equal halves from the start and end, discarding the middle.
        
        Returns:
            The original text if it fits within the token limit, or a truncated version decoded from the
            preserved tokens according to the chosen mode.
        
        Raises:
            ValueError: If an unknown mode is provided.
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
    Class: ModelHandlerFactory
    
    A factory class responsible for creating and managing model handler instances. It centralizes the instantiation and configuration of handlers that interface with various models, ensuring consistent setup and resource management across different model types.
    
        This class is responsible for creating handlers based on the configuration of the class. It supports the creation of handlers for different types of models.
    
        Methods:
         build:
            Builds and returns a model handler instance based on the given configuration.
    """


    @classmethod
    def build(cls, model_settings: ModelSettings) -> ProtollmHandler:
        """
        Builds and returns a handler based on the configuration of the class.
        
        This method retrieves the configuration from the class and then creates and returns a handler using the configuration.
        
        Args:
            model_settings: The model settings to use for the handler.
            cls: The class from which the configuration is retrieved. This is implicitly passed as the first argument to the classmethod.
        
        Returns:
            ProtollmHandler: An instance of the ProtollmHandler, initialized with the provided model settings.
        
        Why:
            This classmethod provides a factory interface to instantiate a ProtollmHandler. It centralizes handler creation, ensuring that the handler is always constructed with the necessary model_settings configuration.
        """
        return ProtollmHandler(model_settings)
