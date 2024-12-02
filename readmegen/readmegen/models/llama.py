"""Self-hosted Llama model handler implementation"""

import uuid
from typing import Any
import requests

from readmegen.models.base import BaseModelHandler
from readmegen.config.settings import ConfigLoader
from readmegen.ingestion.models import RepositoryContext
from readmegen.models.tokens import token_handler


class LLamaHandler(BaseModelHandler):
    """LLama model implementation"""

    def __init__(
            self,
            config_loader: ConfigLoader,
            context: RepositoryContext
    ) -> None:
        super().__init__(config_loader, context)
        self._model_settings()

    def _model_settings(self):
        self.url = self.config.llm.url
        self.temperature = self.config.llm.temperature
        self.tokens = self.config.llm.tokens

    def _build_payload(self, prompt: str, tokens: int, temperature: float) -> dict:
        """Build payload for POST request to OpenAI API."""
        job_id = str(uuid.uuid4())
        message = {
            "job_id": job_id,
            "meta": {"temperature": temperature, "tokens_limit": tokens},
            "content": prompt
        }

        return message

    def _make_request(
            self,
            index: str | None,
            prompt: str | None,
            tokens: int | None,
            temperature: float,
            repo_files: Any,
    ) -> Any:
        """Processes Llama API LLM responses and returns generated text."""
        prompt = token_handler(self.config, index, prompt, tokens)

        parameters = self._build_payload(prompt, tokens, temperature)

        response = requests.post(
            url=self.url,
            json=parameters
        )
        return index, response.json()["content"]
