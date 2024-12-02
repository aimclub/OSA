"""Utility methods to build prompts for LLM text generation."""

from readmegen.config.settings import Settings
from readmegen.ingestion.models import RepositoryContext


def get_prompt_context(prompts: dict, prompt_type: str, context: dict) -> str:
    """Generates a prompt for the LLM API."""
    prompt_template = get_prompt_template(prompts, prompt_type)
    if not prompt_template:
        """TODO: deleted logger"""
        return ""

    return inject_prompt_context(prompt_template, context)


def get_prompt_template(prompts: dict, prompt_type: str) -> str:
    """Retrieves the template for the given prompt type."""
    prompt_templates = {
        "core_features": prompts["prompts"]["core_features"],
        "overview": prompts["prompts"]["overview"]
    }
    return prompt_templates.get(prompt_type, "")


def inject_prompt_context(template: str, context: dict) -> str:
    """Formats the template with the provided context."""
    try:
        return template.format(*[context[key] for key in context])
    except KeyError as exc:
        """TODO: deleted logger"""
        print(f"Missing context for prompt key: {exc}")
        return ""


def set_additional_contexts(
        config: Settings,
        repo_context: RepositoryContext,
        file_summaries: list[tuple[str, str]]
) -> list[dict]:
    """Generates additional prompts (features, overview) for LLM."""
    return [
        {"type": prompt_type, "context": context}
        for prompt_type, context in [
            (
                "core_features",
                {
                    "name": config.git.name,
                    "dependencies": repo_context.dependencies,
                    "quickstart": repo_context.quickstart,
                    "file_summary": file_summaries,
                },
            ),
            (
                "overview",
                {
                    "name": config.git.name,
                    "file_summary": file_summaries,
                }
            )
        ]
    ]


def set_summary_context(
        config: Settings,
        repo_files: list[tuple[str, str]]
) -> list[dict]:
    """Generates the summary prompts to be used by the LLM API."""
    return [
        {"type": prompt_type, "context": context}
        for prompt_type, context in [
            (
                "file_summary",
                {
                    "repo_files": repo_files,
                }
            )
        ]
    ]
