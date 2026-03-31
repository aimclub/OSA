"""Determine the user's intent: generate / improve / update, scope, and paper relevance."""

from __future__ import annotations

from pydantic import ValidationError

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.models import TaskIntent
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError


def intent_analyzer_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Analyze user request + repository state to produce a TaskIntent."""
    logger.info("[IntentAnalyzer] Analyzing user intent...")

    ctx = state.context
    has_existing = bool(ctx and ctx.existing_readme and ctx.existing_readme.strip() != "No README.md file")
    has_attachment = bool(state.attachment and ctx and ctx.pdf_content)

    if not has_existing and not state.user_request:
        intent = TaskIntent(
            task_type="generate",
            scope="full",
            affected_sections=[],
            incorporate_paper=has_attachment,
            reasoning="No existing README found. Generating complete README from scratch.",
        )
        logger.info("[IntentAnalyzer] Fast-path: %s/%s", intent.task_type, intent.scope)
        return {"intent": intent}

    try:
        intent = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme_agent.intent_analysis"),
                repo_analysis=ctx.repo_analysis or "" if ctx else "",
                readme_analysis=ctx.readme_analysis or "" if ctx else "",
                article_analysis=ctx.article_analysis or "N/A" if ctx else "N/A",
                user_request=state.user_request or "Generate a comprehensive README",
                has_existing_readme=str(has_existing),
                has_attachment=str(has_attachment),
            ),
            parser=TaskIntent,
        )
    except (JsonParseError, ValidationError):
        logger.warning("[IntentAnalyzer] LLM parse failed; falling back to heuristics.")
        if has_existing:
            intent = TaskIntent(
                task_type="improve",
                scope="full",
                incorporate_paper=has_attachment,
                reasoning="Fallback: existing README found, defaulting to full improvement.",
            )
        else:
            intent = TaskIntent(
                task_type="generate",
                scope="full",
                incorporate_paper=has_attachment,
                reasoning="Fallback: no existing README, defaulting to full generation.",
            )

    logger.info(
        "[IntentAnalyzer] intent=%s/%s, affected=%s, paper=%s",
        intent.task_type,
        intent.scope,
        intent.affected_sections,
        intent.incorporate_paper,
    )
    logger.debug("[IntentAnalyzer] State after node: %s", state)
    return {"intent": intent}
