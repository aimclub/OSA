from readmeai.config.settings import Settings
from abc import ABC, abstractmethod
from uuid import uuid4
import requests
import logging
import openai
import os
import dotenv


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
            {
                "role": "system",
                "content": "You are a helpful assistant for generating a Python docstrings.",
            },
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


class LlamaHandler(ModelHandler):
    """
    Class: llamaHandler

    This class handles the interaction with a specified URL. It initializes the instance with a provided configuration and sends requests to the URL.

    Methods:
         __init__:
            Initializes the instance with the provided configuration. This method sets the url and config attributes of the instance using the provided Settings object.

         send_request:
            Sends a request to a specified URL with a payload initialized with a given prompt. This method initializes a payload with the provided prompt and configuration, sends a POST request to a specified URL with this payload, and logs the response.
    """

    def __init__(self, config: Settings):
        """
        Initializes the instance with the provided configuration.

        This method sets the url and config attributes of the instance using the provided Settings object.

        Args:
            config: The configuration settings to be used for initializing the instance.

        Returns:
            None
        """
        self.url = os.path.dirname(config.llm.url) + "/chat_completion"
        self.config = config

    def send_request(self, prompt) -> str:
        """
        Sends a request to a specified URL.

        This method sends a request to a specified URL and returns the response.

        Returns:
            str: The response received from the request.
        """
        self.initialize_payload(self.config, prompt)
        response = requests.post(url=self.url, json=self.payload)
        logging.info(response)
        return response.json()["content"]


class OpenaiHandler(ModelHandler):
    """
    This class, openaiHandler, is designed to handle interactions with the OpenAI API. It is initialized with configuration settings and can send requests to the API.

    Methods:
        __init__:
            Initializes the instance with the provided configuration settings. This method sets up the instance by assigning the provided configuration settings to the instance's config attribute. It also retrieves the API from the configuration settings and passes it to the _configure_api method.

        send_request:
            Sends a request to Sam Altman and initializes the payload with the given prompt. This method sends a request to Sam Altman, initializes the payload with the given prompt, and creates a chat completion with the specified model, messages, max tokens, and temperature from the configuration. It then returns the content of the first choice from the response.

        _configure_api:
            Configures the API for the instance based on the provided API name. This method loads environment variables, sets the URL and API key based on the provided API name, and initializes the OpenAI client with the set URL and API key.
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
        api = config.llm.api
        self._configure_api(api)

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
        response = self.client.chat.completions.create(
            model=self.config.llm.model,
            messages=messages,
            max_tokens=self.config.llm.tokens,
            temperature=self.config.llm.temperature,
        )
        return response.choices[0].message.content

    def _configure_api(self, api: str) -> None:
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
        if api == "openai":
            self.url = "https://api.openai.com/v1"
            self.key = os.getenv("OPENAI_API_KEY")
            self.config.llm.tokens = 1500
        if api == "vsegpt":
            self.url = "https://api.vsegpt.ru/v1"
            self.key = os.getenv("VSE_GPT_KEY")

        self.client = openai.OpenAI(base_url=self.url, api_key=self.key)


class ModelHandlerFactory:
    """
    Class: modelHandlerFactory

    This class is responsible for creating handlers based on the configuration of the class. It supports the creation of handlers for different types of models.

    Methods:
     build:
        This method retrieves the configuration from the class
        and then creates and returns a handler using the configuration. The class from which the configuration is
        retrieved is passed as an argument.

     create_handler:
        This method uses the model specified in the configuration to create a handler. It supports three types of
        models: 'llama', 'openai', and 'gpt-4'. For 'llama', it creates a llamaHandler, and for 'openai' and 'gpt-4',
        it creates an openaiHandler. The configuration object which contains the model information is passed as an argument.
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
            None: This method does not return anything.
        """
        return cls.create_handler(config)

    @staticmethod
    def create_handler(config: Settings) -> ModelHandler:
        """
        Creates a handler based on the model specified in the configuration.

        This method uses the model specified in the configuration to create a handler.
        It supports three types of models: 'llama', 'openai', and 'vsegpt'.
        For 'llama', it creates a llamaHandler, and for 'openai' and 'vsegpt', it creates an openaiHandler.

        Args:
            config: The configuration object which contains the model information.

        Returns:
            None: This method does not return anything.
        """
        api = config.llm.api
        constructors = {
            "llama": LlamaHandler,
            "openai": OpenaiHandler,
            "vsegpt": OpenaiHandler,
        }
        return constructors[api](config)
