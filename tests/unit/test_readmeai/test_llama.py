import pytest
import uuid
from unittest.mock import MagicMock

from readmeai.models.llama import LLamaHandler
from readmeai.config.settings import ConfigLoader
from readmeai.ingestion.models import RepositoryContext


@pytest.fixture
def mock_config():
    mock = MagicMock(spec=ConfigLoader)

    mock.config = MagicMock()

    mock.config.llm = MagicMock()
    mock.config.llm.url = "http://llama-api.com"
    mock.config.llm.temperature = 0.05
    mock.config.llm.tokens = 512
    mock.config.llm.encoder = "cl100k_base"
    mock.config.llm.context_window = 200

    mock.config.api = MagicMock()
    mock.config.api.rate_limit = 10

    mock.prompts = MagicMock()
    return mock


@pytest.fixture
def mock_context():
    mock = MagicMock(spec=RepositoryContext)
    mock.dependencies = []
    mock.files = []
    return mock


@pytest.fixture
def mock_token_handler(mocker):
    mocker.patch("readmeai.models.tokens.token_handler",
                 return_value="Generated text."
                 )


@pytest.fixture
def llama_handler(mock_config, mock_context):
    return LLamaHandler(mock_config, mock_context)


@pytest.fixture
def mock_post(mocker):
    return mocker.patch("requests.post")


def test_model_settings(llama_handler):
    assert llama_handler.url == "http://llama-api.com"
    assert llama_handler.temperature == 0.05
    assert llama_handler.tokens == 512


def test_build_payload(llama_handler):
    prompt = "Test prompt"
    tokens = 256
    temperature = 0.5
    payload = llama_handler._build_payload(prompt, tokens, temperature)

    assert "job_id" in payload
    assert uuid.UUID(payload["job_id"])
    assert payload["meta"]["temperature"] == temperature
    assert payload["meta"]["tokens_limit"] == tokens
    assert payload["content"] == prompt


def test_make_request(llama_handler, mock_post, mock_token_handler):
    index = "test_index"
    prompt = "Generate some text."
    tokens = 100
    temperature = 0.7
    repo_files = None

    mock_response = MagicMock()
    mock_response.json.return_value = {"content": "Generated text"}
    mock_post.return_value = mock_response

    result_index, result_text = llama_handler._make_request(
        index, prompt, tokens, temperature, repo_files
    )

    assert result_index == index
    assert result_text == "Generated text"

    assert mock_post.call_count == 1
    assert mock_response.json.call_count == 1

    mock_post.assert_called_once_with(
        url="http://llama-api.com",
        json={
            "job_id": mock_post.call_args[1]["json"]["job_id"],
            "meta": {"temperature": temperature, "tokens_limit": tokens},
            "content": prompt
        }
    )
