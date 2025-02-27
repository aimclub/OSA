"""Utility methods to build prompts for LLM text generation."""

from typing import Dict

from OSA.readmeai.readmegen_article.config.settings import ArticleSettings
from OSA.readmeai.ingestion.models import RepositoryContext
from OSA.readmeai.logger import get_logger

_logger = get_logger(__name__)


def get_prompt_context_article(prompts: dict, prompt_type: str, context: dict) -> str:
    """Generates a prompt for the LLM API."""
    prompt_template = get_prompt_template_article(prompts, prompt_type)
    if not prompt_template:
        _logger.error(f"Prompt type '{prompt_type}' not found.")
        return ""

    return inject_prompt_context_article(prompt_template, context)


def get_prompt_template_article(prompts: dict, prompt_type: str) -> str:
    """Retrieves the template for the given prompt type."""
    prompt_templates = {
        "overview": prompts["prompts"]["overview"],
        "content": prompts["prompts"]["content"],
        "algorithms": prompts["prompts"]["algorithms"],
    }
    return prompt_templates.get(prompt_type, "")


def inject_prompt_context_article(template: str, context: dict) -> str:
    """Formats the template with the provided context."""
    try:
        return template.format(*[context[key] for key in context])
    except KeyError as exc:
        _logger.error(f"Missing context for prompt key: {exc}")
        return ""


def set_additional_contexts_article(
    config: ArticleSettings,
    repo_context: RepositoryContext,
    file_summaries: list[tuple[str, str]],
    pdf_summaries: list[tuple[str, str]]
) -> list[dict]:
    """Generates additional prompts for LLM."""
    return [
        {"type": prompt_type, "context": context}
        for prompt_type, context in [
            (
                "overview",
                {
                    "name": config.git.name,
                    "file_summary": file_summaries,
                    "pdf_summary": pdf_summaries,
                },
            ),
            (
                "content",
                {
                    "name": config.git.name,
                    "dependencies": repo_context.dependencies,
                    "file_summary": file_summaries,
                },
            ),
            (
                "algorithms",
                {
                    "name": config.git.name,
                    "file_summary": file_summaries,
                    "pdf_summary": pdf_summaries,
                },
            ),
        ]
    ]


def set_summary_context_article(
    config: ArticleSettings, repo_files: list[tuple[str, str]]
) -> list[dict]:
    """Generates the summary prompts to be used by the LLM API."""
    return [
        {"type": prompt_type, "context": context}
        for prompt_type, context in [
            (
                "file_summary",
                {
                    "repo_files": repo_files,
                },
            )
        ]
    ]

def set_pdf_summary_context_article(
    config: ArticleSettings, pdf_files: list[tuple[str, str]]
) -> list[dict]:
    """Generates the summary prompts to be used by the LLM API."""
    return [
        {"type": prompt_type, "context": context}
        for prompt_type, context in [
            (
                "pdf_summary",
                {
                    "pdf_files": pdf_files,
                },
            )
        ]
    ]
