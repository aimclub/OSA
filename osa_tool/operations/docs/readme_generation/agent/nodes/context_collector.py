"""Collect repository context: tree, key files, README, PDF, and LLM analyses."""

from __future__ import annotations

import asyncio
import os

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_state, summarize_update
from osa_tool.operations.docs.readme_generation.agent.models import RepositoryContext
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.context.article_content import PdfParser
from osa_tool.operations.docs.readme_generation.context.article_path import get_pdf_path
from osa_tool.operations.docs.readme_generation.llm_schemas import KeyFilesLLMOutput
from osa_tool.operations.docs.readme_generation.utils import extract_example_paths, read_file
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.token_counter import count_tokens, truncate_to_tokens
from osa_tool.utils.utils import extract_readme_content, parse_folder_name

_IMPORTANT_FILENAMES = frozenset(
    {
        "__init__.py",
        "__main__.py",
        "main.py",
        "app.py",
        "cli.py",
        "setup.py",
        "setup.cfg",
        "pyproject.toml",
        "Cargo.toml",
        "package.json",
        "go.mod",
        "Makefile",
        "Dockerfile",
        "requirements.txt",
        "environment.yml",
    }
)


def _compute_budgets(context_window: int, max_output_tokens: int) -> dict[str, int]:
    """Compute token budgets for each context component.

    Uses percentage-based allocation with hard caps to prevent
    excessively large budgets on wide context windows.
    """
    available = context_window - max_output_tokens - 200
    available = max(available, 1000)
    return {
        "tree": min(4000, int(available * 0.30)),
        "existing_readme": min(4000, int(available * 0.25)),
        "key_files": min(6000, int(available * 0.40)),
        "examples": min(2000, int(available * 0.10)),
        "pdf": min(3000, int(available * 0.20)),
    }


def _truncate_tree(tree: str, max_tokens: int, encoding_name: str) -> str:
    """Smart tree truncation preserving structural overview.

    Strategy:
      1. Keep all entries at depth <= 2 (top-level structure).
      2. At depth 3+, keep directories and important filenames only.
      3. If still over budget, hard-truncate with truncate_to_tokens.
    """
    if not tree or max_tokens <= 0:
        return ""

    if count_tokens(tree, encoding_name) <= max_tokens:
        return tree

    pruned_lines = []
    for line in tree.splitlines():
        depth = line.count("/")
        if depth <= 1:
            pruned_lines.append(line)
        else:
            basename = line.rsplit("/", 1)[-1] if "/" in line else line
            if "." not in basename or basename in _IMPORTANT_FILENAMES:
                pruned_lines.append(line)

    pruned = "\n".join(pruned_lines)

    if count_tokens(pruned, encoding_name) <= max_tokens:
        return pruned

    return truncate_to_tokens(pruned, max_tokens, encoding_name, mode="start")


def _read_files_with_budget(
    repo_path: str,
    file_paths: list[str],
    total_budget: int,
    per_file_cap: int,
    encoding_name: str,
) -> tuple[list[str], str]:
    """Read files in priority order until token budget is exhausted."""
    if not file_paths or total_budget <= 0:
        return [], ""

    remaining = total_budget
    read_paths: list[str] = []
    parts: list[str] = []

    for file_path in file_paths:
        if remaining <= 0:
            break

        abs_path = os.path.join(repo_path, file_path)
        raw_content = read_file(abs_path)
        if not raw_content:
            continue

        cap = min(per_file_cap, remaining)
        content = truncate_to_tokens(raw_content, cap, encoding_name, mode="start")
        tokens_used = count_tokens(content, encoding_name)

        name = os.path.basename(file_path)
        parts.append(f"### {name} ({file_path})\n{content}")
        read_paths.append(file_path)
        remaining -= tokens_used

    return read_paths, "\n\n".join(parts)


def _run_parallel_analyses(
    context: ReadmeContext,
    repo_tree: str,
    existing_readme: str,
    repo_analysis: str | None,
    pdf_content: str | None,
) -> tuple[str | None, str | None]:
    """Run readme_analysis and article_analysis concurrently."""

    async def _gather() -> list:
        tasks = [
            context.model_handler.async_send_and_parse(
                prompt=PromptBuilder.render(
                    context.prompts.get("readme_agent.readme_analysis"),
                    existing_readme=existing_readme,
                    repo_analysis=repo_analysis or "",
                    repository_tree=repo_tree,
                ),
                parser=LlmTextOutput,
            ),
        ]
        if pdf_content:
            tasks.append(
                context.model_handler.async_send_and_parse(
                    prompt=PromptBuilder.render(
                        context.prompts.get("readme_agent.article_analysis"),
                        pdf_content=pdf_content,
                        repo_analysis=repo_analysis or "",
                        existing_readme=existing_readme,
                    ),
                    parser=LlmTextOutput,
                ),
            )
        return await asyncio.gather(*tasks, return_exceptions=True)

    results = asyncio.run(_gather())

    readme_analysis = None
    r0 = results[0]
    if isinstance(r0, BaseException):
        logger.error("[ContextCollector] readme_analysis failed: %s", r0)
    elif r0 is not None:
        readme_analysis = r0.text

    article_analysis = None
    if len(results) > 1:
        r1 = results[1]
        if isinstance(r1, BaseException):
            logger.error("[ContextCollector] article_analysis failed: %s", r1)
        elif r1 is not None:
            article_analysis = r1.text

    return readme_analysis, article_analysis


def _gather_raw_context(
    state: ReadmeState,
    context: ReadmeContext,
    budgets: dict[str, int],
    encoding: str,
) -> dict:
    """Phase 1: Gather raw repository context (tree, files, README, PDF)."""
    sourcerank = SourceRank(context.config_manager)
    repo_path = os.path.join(os.getcwd(), parse_folder_name(state.repo_url))
    raw_tree = sourcerank.tree
    repo_tree = _truncate_tree(raw_tree, budgets["tree"], encoding)
    logger.info(
        "[ContextCollector] Tree: %d tokens (raw %d tokens)",
        count_tokens(repo_tree, encoding),
        count_tokens(raw_tree, encoding),
    )

    raw_readme = extract_readme_content(repo_path)
    existing_readme = truncate_to_tokens(raw_readme, budgets["existing_readme"], encoding)

    key_files = (
        context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme.preanalysis"),
                repository_tree=repo_tree,
                readme_content=existing_readme,
            ),
            parser=KeyFilesLLMOutput,
        ).key_files
        or []
    )
    logger.info("[ContextCollector] LLM selected %d key files", len(key_files))

    per_file_cap = min(2000, budgets["key_files"] // 3) if budgets["key_files"] > 0 else 0
    key_files_read, key_files_content = _read_files_with_budget(
        repo_path, key_files, budgets["key_files"], per_file_cap, encoding
    )
    logger.info(
        "[ContextCollector] Read %d/%d key files (%d tokens)",
        len(key_files_read),
        len(key_files),
        count_tokens(key_files_content, encoding),
    )

    examples_files = extract_example_paths(raw_tree)
    examples_cap = min(800, budgets["examples"] // 3) if budgets["examples"] > 0 else 0
    _, examples_content = _read_files_with_budget(
        repo_path, examples_files, budgets["examples"], examples_cap, encoding
    )

    pdf_content = None
    if state.attachment:
        path_to_pdf = get_pdf_path(state.attachment)
        if path_to_pdf:
            raw_pdf = PdfParser(path_to_pdf).data_extractor()
            if raw_pdf:
                pdf_content = truncate_to_tokens(raw_pdf, budgets["pdf"], encoding)

    return {
        "repo_tree": repo_tree,
        "existing_readme": existing_readme,
        "key_files": key_files_read,
        "key_files_content": key_files_content,
        "examples_content": examples_content,
        "pdf_content": pdf_content,
    }


def _run_llm_analyses(context: ReadmeContext, raw_ctx: dict) -> dict:
    """Phase 2: Run LLM analyses on gathered context.

    repo_analysis runs first (others depend on it), then
    readme_analysis and article_analysis run in parallel.
    """
    repo_analysis = context.model_handler.send_and_parse(
        prompt=PromptBuilder.render(
            context.prompts.get("readme_agent.repo_analysis"),
            repository_tree=raw_ctx["repo_tree"],
            key_files_content=raw_ctx["key_files_content"],
            existing_readme=raw_ctx["existing_readme"],
        ),
        parser=LlmTextOutput,
    ).text

    readme_analysis, article_analysis = _run_parallel_analyses(
        context,
        raw_ctx["repo_tree"],
        raw_ctx["existing_readme"],
        repo_analysis,
        raw_ctx["pdf_content"],
    )

    return {
        "repo_analysis": repo_analysis,
        "readme_analysis": readme_analysis,
        "article_analysis": article_analysis,
    }


def context_collector_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Collect repository context and return it as a RepositoryContext object."""
    logger.info("[ContextCollector] Gathering repository context...")
    logger.debug("[ContextCollector] Input state summary: %s", summarize_state(state))

    model_settings = context.config_manager.get_model_settings("readme")
    encoding = model_settings.encoder
    budgets = _compute_budgets(model_settings.context_window, model_settings.max_tokens)
    logger.info("[ContextCollector] Token budgets: %s", budgets)

    raw_ctx = _gather_raw_context(state, context, budgets, encoding)
    analyses = _run_llm_analyses(context, raw_ctx)

    repo_context = RepositoryContext(
        repo_tree=raw_ctx["repo_tree"],
        existing_readme=raw_ctx["existing_readme"],
        key_files=raw_ctx["key_files"],
        key_files_content=raw_ctx["key_files_content"],
        examples_content=raw_ctx["examples_content"],
        pdf_content=raw_ctx["pdf_content"],
        repo_analysis=analyses["repo_analysis"],
        readme_analysis=analyses["readme_analysis"],
        article_analysis=analyses["article_analysis"],
    )

    update = {"context": repo_context}
    logger.debug("[ContextCollector] Output update summary: %s", summarize_update(update))
    logger.info("[ContextCollector] Context collection complete.")
    return update
