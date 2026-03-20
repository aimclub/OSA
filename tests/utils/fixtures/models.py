import pytest


class DummyResponse:
    """
    A dummy HTTP response class for testing purposes.
    
        This class simulates an HTTP response object, providing a simplified interface
        for testing code that interacts with HTTP responses without making actual network
        requests.
    
        Attributes:
            content: The raw response content as bytes or string.
            status_code: The HTTP status code of the response.
            headers: A dictionary containing response headers.
    
        Methods:
            __init__: Initializes a new dummy response with content, status code, and headers.
            json: Parses the response content as JSON and returns the parsed object.
            raise_for_status: Raises an exception if the status code indicates an error.
    """

    def __init__(self, content):
        """
        Initializes a new instance of the DummyResponse class with the provided content.
        
        Args:
            content: The content to be stored in the instance. This content is typically used to simulate or mock a response payload for testing or placeholder purposes.
        
        Attributes:
            content: Stores the content provided during initialization.
        """
        self.content = content


class DummyLLMClient:
    """
    DummyLLMClient is a mock client for testing language model interactions without making actual API calls.
    
        Attributes:
            model_name: The name of the dummy model being simulated.
            temperature: Controls randomness in the dummy responses.
            max_tokens: Maximum number of tokens in generated dummy responses.
    
        Methods:
            invoke: Synchronously generates a dummy response based on input messages.
            ainvoke: Asynchronously generates a dummy response based on input messages.
    """


    @staticmethod
    def invoke(messages):
        """
        Generates a dummy synchronous response based on the provided messages.
        This method is a static utility that simulates a synchronous API call, returning a predefined static response. It is primarily used for testing or as a placeholder when a real language model client is not available or needed.
        
        Args:
            messages: A list of messages or input data to process. The content of this parameter is ignored, as the response is static.
        
        Returns:
            DummyResponse: An object containing a static "sync response" content.
        """
        return DummyResponse(content="sync response")

    @staticmethod
    async def ainvoke(messages):
        """
        Asynchronously invokes the model with a list of messages and returns a dummy response.
        This method is a static, asynchronous placeholder used for testing or when a real model client is not available, allowing asynchronous operations to be simulated without external dependencies.
        
        Args:
            messages: The list of messages to be processed by the model. This input is accepted to maintain interface compatibility with real model clients but is not used in generating the response.
        
        Returns:
            DummyResponse: An object containing a fixed placeholder response content ("async response").
        """
        return DummyResponse(content="async response")


@pytest.fixture
def patch_llm_connector(monkeypatch):
    """
    Patch the `create_llm_connector` function to return a dummy client for testing.
    
    This method uses `monkeypatch` to replace the real LLM connector creation with a lambda that returns a `DummyLLMClient` instance. This is useful in testing to avoid making actual external API calls, ensuring tests are fast, reliable, and isolated.
    
    Args:
        monkeypatch: A pytest monkeypatch object used to dynamically replace attributes during testing.
    
    Returns:
        None
    """
    monkeypatch.setattr("osa_tool.core.llm.llm.create_llm_connector", lambda *args, **kwargs: DummyLLMClient())
