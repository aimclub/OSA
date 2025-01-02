import asyncio
from abc import ABC, abstractmethod
from collections.abc import Generator

from typing import Any

import aiohttp

from readmegen.config.settings import ConfigLoader
from readmegen.ingestion.models import RepositoryContext
from readmegen.models.prompts import (
    get_prompt_context,
    set_additional_contexts,
    set_summary_context,
)
from readmegen.models.tokens import update_max_tokens


class BaseModelHandler(ABC):
    """
    Interface for LLM API handler implementations.
    """

    def __init__(
        self, config_loader: ConfigLoader, context: RepositoryContext
    ) -> None:
        self._session: aiohttp.ClientSession | None = None
        self.config = config_loader.config
        self.placeholder = self.config.md.placeholder
        self.prompts = config_loader.prompts
        self.max_tokens = self.config.llm.tokens
        self.rate_limit = self.config.api.rate_limit
        self.rate_limit_semaphore = asyncio.Semaphore(self.rate_limit)
        self.temperature = self.config.llm.temperature
        self.system_message = self.config.api.system_message
        self.repo_context = context
        self.dependencies = context.dependencies
        self.documents = [
            (file.path, file.content)
            for file in context.files
            if ".lock" not in file.name
        ]

    @abstractmethod
    def _model_settings(self) -> None:
        """Initializes LLM API settings for a given service."""
        ...

    @abstractmethod
    def _build_payload(
        self, prompt: str, tokens: int, temperature: float
    ) -> dict[str, Any]:
        """Builds the payload for the POST request to the LLM API."""
        ...

    @abstractmethod
    def _make_request(
        self,
        index: str | None,
        prompt: str | None,
        tokens: int | None,
        temperature: float,
        repo_files: list[tuple[str, str]] | None,
    ) -> Any:
        """Handles LLM API response and returns the generated text."""
        ...

    def batch_request(self) -> list[tuple[str, str]]:
        """Generates a batch of prompts and processes the responses."""
        summaries_prompts = set_summary_context(self.config, self.documents)

        summaries_responses = self._batch_prompts(summaries_prompts)
        additional_prompts = set_additional_contexts(
            self.config, self.repo_context, summaries_responses
        )
        additional_responses = self._batch_prompts(additional_prompts)

        return summaries_responses + additional_responses

    def _batch_prompts(
        self, prompts: Any, batch_size=10
    ) -> list[tuple[str, str]]:
        """Processes a batch of prompts and returns the generated text."""
        responses = []
        for batch in self._generate_batches(prompts, batch_size):
            batch_responses = []
            for prompt in batch:
                response = self._process_batch(prompt)
                batch_responses.append(response)
            responses.extend(batch_responses)

        return responses

    def _generate_batches(
        self, items: list[Any], batch_size: int
    ) -> Generator[list[Any], None, None]:
        """Generates batches of items to be processed."""
        for i in range(0, len(items), batch_size):
            yield items[i : i + batch_size]

    def _process_batch(self, prompt: dict[str, Any]) -> Any:
        """Processes a single prompt and returns the generated text."""
        if prompt["type"] == "file_summary":
            return self._make_request_code_summary(
                prompt["context"],
            )
        else:
            formatted_prompt = get_prompt_context(
                self.prompts,
                prompt["type"],
                prompt["context"],
            )
            tokens = update_max_tokens(
                self.config.llm.tokens,
                formatted_prompt,
            )
            temperature = self.temperature

            _, summary = self._make_request(
                prompt["type"],
                formatted_prompt,
                tokens,
                temperature,
                None,
            )
            return summary

    def _make_request_code_summary(
        self,
        file_context: list[tuple[str, str]],
    ) -> Any:
        """Generates code summaries for each file in the project."""
        files = [file[0] for file in file_context["repo_files"]]
        prompt = self.prompts["prompts"]["file_summary"].format(
            files,
        )
        tokens = update_max_tokens(self.config.llm.tokens, prompt)
        temperature = self.temperature
        _, summary_or_error = self._make_request(
            "list of files",
            prompt,
            tokens,
            temperature,
            None,
        )

        return summary_or_error
