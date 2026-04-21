import asyncio
import os
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import networkx as nx
import tiktoken
import torch
from rich.progress import track
from torch.nn import functional
from transformers import AutoTokenizer, AutoModel

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.core.models.llm_output_models import LlmJsonObject
from osa_tool.operations.analysis.repository_validation.analyze.paper_analyzer import (
    PaperAnalyzer,
)
from osa_tool.operations.analysis.repository_validation.analyze.code_analyzer import (
    CodeAnalyzer,
)
from osa_tool.operations.analysis.repository_validation.experiment import Experiment
from osa_tool.operations.analysis.repository_validation.report_generator import (
    ReportGenerator as ValidationReportGenerator,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


@dataclass
class _LLMPromptContext:
    """
    All data needed to be fed into an LLM for a single experiment assessment.
    """

    experiment: str
    retrieved_nodes: list[dict]


class PaperValidator:
    """
    Validates a scientific paper against the code repository.

    This class extracts and processes the content of a paper, analyzes code files in the repository,
    and validates the paper against the codebase using a language model.
    """

    def __init__(
        self, config_manager: ConfigManager, git_agent: GitAgent, create_fork: bool, attachment: str | None = None
    ):
        """
        Initialize the PaperValidator.

        Args:
            config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
            git_agent (GitAgent): Abstract base class for Git platform agents.
            create_fork (bool): The flag is responsible for creating a pull request.
            attachment (str | None): Path to the paper PDF file.
        """
        self.__config_manager = config_manager
        self.__git_agent = git_agent
        self.__create_fork = create_fork
        self.__path_to_article = attachment
        self.__events: list[OperationEvent] = []

        self.__prompts = self.__config_manager.get_prompts()
        self.__model_settings = self.__config_manager.get_model_settings("validation")
        self.__model_handler: ModelHandler = ModelHandlerFactory.build(self.__model_settings)

        self.__code_analyzer = CodeAnalyzer(config_manager)
        self.__paper_analyzer = PaperAnalyzer(config_manager, self.__prompts)
        self.__experiments = []

    def run(self) -> dict:
        try:
            return asyncio.run(self._run_async())
        except ValueError as e:
            self.__events.append(
                OperationEvent(kind=EventKind.FAILED, target="Paper validation", data={"error": str(e)})
            )
            return {"result": {"error": str(e)}, "events": self.__events}

    async def _run_async(self) -> dict:
        content = await self.validate()

        if content:
            va_re_gen = ValidationReportGenerator(self.__config_manager, self.__git_agent.metadata)
            va_re_gen.build_pdf("Paper", content)

            self.__events.append(OperationEvent(kind=EventKind.GENERATED, target=va_re_gen.filename))

            if self.__create_fork and os.path.exists(va_re_gen.output_path):
                self.__git_agent.upload_report(va_re_gen.filename, va_re_gen.output_path)
                self.__events.append(OperationEvent(kind=EventKind.UPLOADED, target=va_re_gen.filename))

            return {"result": {"report": va_re_gen.filename}, "events": self.__events}

        logger.warning("Paper validation returned no content. Skipping report generation.")
        self.__events.append(
            OperationEvent(
                kind=EventKind.SKIPPED,
                target="Paper validation",
                data={"reason": "no content"},
            )
        )
        return {"result": None, "events": self.__events}

    async def validate(self) -> list[Experiment, ...]:
        """
        Asynchronously validate a scientific paper against the code repository.

        Returns:
            dict | None: Validation result from the language model or none if an error occurs.

        Raises:
            ValueError: If the article path is missing.
            Exception: If an error occurs during validation.
        """
        if not self.__path_to_article:
            raise ValueError("Article is missing! Please pass it using --attachment argument.")
        try:
            experiments_list = await self.__paper_analyzer.extract_experiments(self.__path_to_article)
            experiment_retriever = _PromptContextBuilder(self.__code_analyzer.repo_graph)
            experiments_contexts = experiment_retriever.retrieve(experiments_list)
            await self.__validate_paper_against_repo(experiments_contexts)
            return self.__experiments
        except Exception as e:
            logger.error(f"Error while validating paper against repo: {e}")
            raise

    async def __validate_paper_against_repo(self, llm_prompt_contexts: list[_LLMPromptContext]):
        """
        Asynchronously compose a validation assessment of the paper content against the code repository.

        Args:
            llm_prompt_contexts (list): Aggregated code files analysis.
        """
        logger.info("Validating paper against repository ...")
        for context in track(llm_prompt_contexts, description="Assessing experiments"):
            code_chunks = ""
            for i, node in enumerate(context.retrieved_nodes, 1):
                code_chunks += f"""snippet {i}:
                type: {node["node_type"]}, name:{node["name"]}, relevance_score:{node["score"]}
                {node["source"]}
                """

            prompt = PromptBuilder.render(
                self.__prompts.get("validation.validate_single_experiment_preprocessed"),
                experiment_description=context.experiment,
                code_snippets=code_chunks,
            )
            experiment_assessment = (
                await self.__model_handler.async_send_and_parse(
                    prompt=prompt,
                    parser=LlmJsonObject,
                )
            ).root

            input_tokens = tiktoken.get_encoding("cl100k_base").encode(prompt)
            logger.info(f"Tokens used: {len(input_tokens)}")
            # logger.info(prompt)

            self.__experiments.append(
                Experiment(
                    description_from_paper=context.experiment,
                    impl_src_path=experiment_assessment["implemented_in"],
                    missing=experiment_assessment["missing_critical_components"],
                    correspondence_percent=experiment_assessment["correlation_percent"],
                    reasoning=experiment_assessment["reasoning"],
                )
            )


class _PromptContextBuilder:
    """
    Embeds experiment descriptions and retrieves the most
    relevant graph nodes for each experiment.
    """

    MODEL_NAME = "sentence-transformers/all-mpnet-base-v2"
    MAX_TOKENS = 1024
    TOP_K = 5  # number of nodes with the minimal cosine similarity
    NODE_TYPE_PRIORITY = {"function": 1.0, "class": 0.6, "module": 0.3}
    SIMILARITY_WEIGHT = 0.7
    PRIORITY_WEIGHT = 0.3

    def __init__(self, graph: nx.DiGraph, device: Optional[str] = None):
        self.__graph = graph
        self.__device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.__tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.__model = AutoModel.from_pretrained(self.MODEL_NAME).to(self.__device)
        self.__model.eval()

        self.__node_ids, self.__node_matrix, self.__node_attrs = self.__build_node_matrix()

    def retrieve(self, experiments: list[str]) -> list[_LLMPromptContext]:
        """
        Process each experiment formulation and build a list of LLMPromptContext objects
        """
        return [self.__get_llm_prompt_context(experiment) for experiment in experiments]

    def __get_llm_prompt_context(self, experiment: str) -> _LLMPromptContext:
        """
        Embed a single experiment description, score all graph nodes,
        retrieves top-k and constructs the LLM prompt.
        """
        scores = self.__score_nodes(self.__embed_text(experiment))
        top_k_indices = scores.topk(min(self.TOP_K, len(self.__node_ids))).indices.tolist()
        retrieved_nodes = []

        for idx in top_k_indices:
            attrs = self.__node_attrs[idx]
            retrieved_nodes.append(
                {
                    "node_id": self.__node_ids[idx],
                    "node_type": attrs.get("node_type", "unknown"),
                    "name": attrs.get("name", ""),
                    "source": attrs.get("source", ""),
                    "score": round(scores[idx].item(), 4),
                }
            )

        return _LLMPromptContext(experiment, retrieved_nodes)

    def __score_nodes(self, exp_embedding: torch.Tensor) -> torch.Tensor:
        """
        Compute a weighted score for each node combining cosine similarity
        to the experiment embedding and a node type priority weight.
        """
        similarity = functional.cosine_similarity(
            exp_embedding.unsqueeze(0),
            self.__node_matrix,
            dim=-1,
        )

        priority = torch.tensor(
            [self.NODE_TYPE_PRIORITY.get(attrs.get("node_type", "function"), 0.3) for attrs in self.__node_attrs],
            dtype=torch.float,
            device=self.__device,
        )

        return self.SIMILARITY_WEIGHT * similarity + self.PRIORITY_WEIGHT * priority

    def __build_node_matrix(self) -> tuple[list[str], torch.Tensor, list[dict]]:
        """
        Extract node embeddings from the graph into a tensor
        """
        node_ids, embeddings, attrs_list = [], [], []

        for node_id, attrs in self.__graph.nodes(data=True):
            emb = attrs.get("embedding")
            if emb is None:
                continue
            node_ids.append(node_id)
            embeddings.append(emb)
            attrs_list.append(attrs)

        matrix = torch.tensor(embeddings, dtype=torch.float, device=self.__device)
        return node_ids, matrix, attrs_list

    def __embed_text(self, text: str) -> torch.Tensor:
        """
        Embeds a text string and returns the CLS token vector.
        """
        tokens = self.__tokenizer(
            text,
            return_tensors="pt",
            max_length=self.MAX_TOKENS,
            truncation=True,
            padding="max_length",
        )
        tokens = {k: v.to(self.__device) for k, v in tokens.items()}

        with torch.no_grad():
            output = self.__model(**tokens)

        return output.last_hidden_state[:, 0, :].squeeze()
