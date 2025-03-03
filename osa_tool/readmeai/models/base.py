import asyncio
from abc import ABC, abstractmethod
from collections.abc import Generator

from typing import Any, Optional

import aiohttp
from typing import Union

from osa_tool.readmeai.readmegen_article.parser.article_finder import ArticleFinder
from osa_tool.readmeai.readmegen_article.parser.pdf_parser import PdfParser
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.readmeai.config.settings import ConfigLoader
from osa_tool.readmeai.ingestion.models import RepositoryContext
from osa_tool.readmeai.models.prompts import (
    get_prompt_context,
    set_additional_contexts,
    set_summary_context,
)
from osa_tool.readmeai.readmegen_article.models.prompts import (
    get_prompt_context_article,
    set_additional_contexts_article,
    set_summary_context_article,
    set_pdf_summary_context_article,
)
from osa_tool.readmeai.models.tokens import update_max_tokens
from osa_tool.osatreesitter.models import ModelHandlerFactory, ModelHandler


class BaseModelHandler:
    """
    Interface for LLM API handler implementations.
    """

    def __init__(
        self, config_loader: Union[ConfigLoader, ArticleConfigLoader], 
        context: RepositoryContext
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
        self.model_handler: ModelHandler = ModelHandlerFactory.build(
            self.config)

    def batch_request(self) -> list[tuple[str, str]]:
        """Generates a batch of prompts and processes the responses."""
        summaries_prompts = set_summary_context(self.config, self.documents)

        summaries_responses = self._batch_prompts(summaries_prompts)
        additional_prompts = set_additional_contexts(
            self.config, self.repo_context, summaries_responses
        )
        additional_responses = self._batch_prompts(additional_prompts)

        return summaries_responses + additional_responses
    
    def article_batch_request(self, article: Optional[str] = None) -> list[tuple[str, str]]:
        """Generates a batch of prompts and processes the responses."""
        summaries_prompts = set_summary_context_article(self.config, self.documents)
        summaries_responses = self._article_batch_prompts(summaries_prompts)

        if article is True:
            article_finder = ArticleFinder(self.config, self.repo_context)
        else:
            article_finder = ArticleFinder(self.config, self.repo_context, article)
        pdf_parser = PdfParser(article_finder.get_pdf_paths)
        pdf_documents = pdf_parser.data_extractor()
        pdf_summaries_prompts = set_pdf_summary_context_article(self.config, pdf_documents)
        pdf_summaries_responses = self._article_batch_prompts(pdf_summaries_prompts)

        additional_prompts = set_additional_contexts_article(
            self.config, self.repo_context, summaries_responses, pdf_summaries_responses
        )
        additional_responses = self._article_batch_prompts(additional_prompts)

        return summaries_responses + pdf_summaries_responses + additional_responses

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
    
    def _article_batch_prompts(
        self, prompts: Any, batch_size=10
    ) -> list[tuple[str, str]]:
        """Processes a batch of prompts and returns the generated text."""
        responses = []
        for batch in self._generate_batches(prompts, batch_size):
            batch_responses = []
            for prompt in batch:
                response = self._article_process_batch(prompt)
                batch_responses.append(response)
            responses.extend(batch_responses)

        return responses

    def _generate_batches(
        self, items: list[Any], batch_size: int
    ) -> Generator[list[Any], None, None]:
        """Generates batches of items to be processed."""
        for i in range(0, len(items), batch_size):
            yield items[i: i + batch_size]

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
            response = self.model_handler.send_request(formatted_prompt)
            return response
        
    def _article_process_batch(self, prompt: dict[str, Any]) -> Any:
        """Processes a single prompt and returns the generated text."""
        if prompt["type"] == "file_summary":
            return self.model_handler.send_request(prompt["context"])
        elif prompt["type"] == "pdf_summary":
            return self.model_handler.send_request(prompt["context"])
        else:
            formatted_prompt = get_prompt_context_article(
                self.prompts,
                prompt["type"],
                prompt["context"],
            )
            response = self.model_handler.send_request(formatted_prompt)
            return response

    def _make_request_code_summary(
        self,
        file_context: list[tuple[str, str]],
    ) -> Any:
        """Generates code summaries for each file in the project."""
        files = [file[0] for file in file_context["repo_files"]]
        prompt = self.prompts["prompts"]["file_summary"].format(
            files,
        )
        response = self.model_handler.send_request(prompt)
        return response
    
    def _make_request_pdf_summary(
        self,
        file_context: list[tuple[str, str]],
    ) -> Any:
        """Generates summaries for pdf files."""
        files = [file[0] for file in file_context["pdf_files"]]
        prompt = self.prompts["prompts"]["pdf_summary"].format(
            files,
        )
        response = self.model_handler.send_request(prompt)
        return response
