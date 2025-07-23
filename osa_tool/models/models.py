from abc import ABC, abstractmethod
from uuid import uuid4

import dotenv
from protollm.connectors import create_llm_connector
from langchain.schema import SystemMessage
from osa_tool.config.settings import Settings


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
    def send_request(self, prompt: str) -> str: ...

    def initialize_payload(self, config: Settings, prompt: str) -> None:
        """
        Initializes the payload for the instance.

        This method uses the provided configuration and prompt to generate a payload using the payloadFactory.
        The generated payload is then converted to payload completions and stored in the instance's payload attribute.

        Args:
            config: The configuration settings to be used for payload generation.
            prompt: The prompt to be used for payload generation.

        Returns:
            None
        """
        self.payload = PayloadFactory(config, prompt).to_payload_completions()


class PayloadFactory:
    """
    Class: payloadFactory

    This class is responsible for creating payloads from instance variables. It is initialized with a unique job ID, temperature, tokens limit, prompt, and roles. The payloads can be used for serialization or for sending the instance data over a network.

    Methods:
     __init__:
        Initializes the instance with a unique job ID, temperature, tokens limit, prompt, and roles. The 'config' parameter should include 'llm' with 'temperature' and 'tokens' attributes. The 'prompt' parameter is the initial user prompt.

     to_payload:
        Converts the instance variables to a dictionary payload. This method takes the instance variables job_id, temperature, tokens_limit, and prompt and packages them into a dictionary. The returned dictionary has the following structure:
            {
                "job_id": job_id,
                "meta": {
                    "temperature": temperature,
                    "tokens_limit": tokens_limit,
                },
                "content": prompt,
            }

     to_payload_completions:
        Converts the instance variables to a dictionary payload for completions. This method returns a dictionary with keys 'job_id', 'meta', and 'messages'. The 'meta' key contains a nested dictionary with keys 'temperature' and 'tokens_limit'. The values for these keys are taken from the instance variables of the same names.
    """

    def __init__(self, config: Settings, prompt: str):
        """
        Initializes the instance with a unique job ID, temperature, tokens limit, prompt, and roles.

        Args:
            config: The configuration settings for the instance. It should include 'llm'
                               with 'temperature' and 'tokens' attributes.
            prompt: The initial user prompt.

        Returns:
            None
        """
        self.job_id = str(uuid4())
        self.temperature = config.llm.temperature
        self.tokens_limit = config.llm.tokens
        self.prompt = prompt
        self.roles = [
            SystemMessage(content="You are a helpful assistant for analyzing open-source repositories."),
            {"role": "user", "content": prompt},
        ]

    def to_payload(self) -> dict:
        """
        Converts the instance variables to a dictionary payload.

        This method takes the instance variables job_id, temperature, tokens_limit, and prompt and
        packages them into a dictionary. This can be useful for serialization or for sending the
        instance data over a network.

        No parameters are required as it uses instance variables.

        Returns:
            dict: A dictionary containing the instance variables. The dictionary has the following structure:
                {
                    "job_id": job_id,
                    "meta": {
                        "temperature": temperature,
                        "tokens_limit": tokens_limit,
                    },
                    "content": prompt,
                }
        """
        return {
            "job_id": self.job_id,
            "meta": {
                "temperature": self.temperature,
                "tokens_limit": self.tokens_limit,
            },
            "content": self.prompt,
        }

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

    def __init__(self, config: Settings):
        """
        Initializes the instance with the provided configuration settings.
        This method sets up the instance by assigning the provided configuration settings to the instance's config attribute.
        It also retrieves the API from the configuration settings and passes it to the _configure_api method.
        Args:
            config: The configuration settings to be used for setting up the instance.
        Returns:
            None
        """
        self.config = config
        self._configure_api(config.llm.api, model_name=config.llm.model)

    def send_request(self, prompt: str) -> str:
        """
        Sends a request to a specified URL with a payload initialized with a given prompt.

        This method initializes a payload with the provided prompt and configuration,
        sends a POST request to a specified URL with this payload, and logs the response.

        Args:
            prompt: The prompt to initialize the payload with.

        Returns:
            str: The response received from the request.
        """
        self.initialize_payload(self.config, prompt)
        messages = self.payload["messages"]
        response = self.client.invoke(messages)
        return response.content

    def _build_model_url(self) -> str:
        """Builds the model URL based on the LLM API type."""
        url_templates = {
            "llama": f"self_hosted;{self.config.llm.itmo_local_url};{self.config.llm.model}",
            "ollama": f"ollama;{self.config.llm.localhost};{self.config.llm.model}",
        }
        return url_templates.get(self.config.llm.api, f"{self.config.llm.url};{self.config.llm.model}")

    def _get_llm_params(self):
        """Extract LLM parameters from config"""
        llm_params = ["temperature", "max_tokens", "top_p"]

        return {
            name: getattr(self.config.llm, name)
            for name in llm_params
            if getattr(self.config.llm, name, None) is not None
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
        connector_creator = create_llm_connector

        model_url = self._build_model_url()
        llm_params = self._get_llm_params()

        self.client = connector_creator(model_url, **llm_params)


class ModelHandlerFactory:
    """
    Class: modelHandlerFactory

    This class is responsible for creating handlers based on the configuration of the class. It supports the creation of handlers for different types of models.

    Methods:
     build:
        Builds and returns a model handler instance based on the given configuration.
    """

    @classmethod
    def build(cls, config: Settings) -> ModelHandler:
        """
        Builds and returns a handler based on the configuration of the class.

        This method retrieves the configuration from the class
        and then creates and returns a handler using the configuration.

        Args:
            config: The configuration object which contains the model information.
            cls: The class from which the configuration is retrieved.

        Returns:
            ModelHandler: An instance of the appropriate model handler.
        """
        return ProtollmHandler(config)
