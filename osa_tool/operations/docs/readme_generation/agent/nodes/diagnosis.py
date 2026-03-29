from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from pydantic import ValidationError

from osa_tool.operations.docs.readme_generation.llm_schemas import DiagnosisLLMOutput
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError


def diagnosis_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Decide generation_mode (full_regen/targeted) and readme_mode (standard/article)."""
    logger.info("[Diagnosis] Analyzing README state and planning generation strategy...")

    readme_mode = "article" if (state.attachment and state.pdf_content) else "standard"

    existing_is_empty = (
        not state.existing_readme
        or state.existing_readme.strip() == "No README.md file"
    )

    # Fast path: no existing README → always full_regen, skip LLM
    if existing_is_empty:
        logger.info("[Diagnosis] mode=full_regen, readme_mode=%s (no existing README)", readme_mode)
        return {
            "readme_mode": readme_mode,
            "generation_mode": "full_regen",
            "generation_plan": "No existing README found. Generating complete README from scratch.",
            "target_sections": [],
        }

    # Use LLM to decide generation strategy
    try:
        diagnosis = context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(
                context.prompts.get("readme_agent.diagnosis"),
                repo_analysis=state.repo_analysis or "",
                readme_analysis=state.readme_analysis or "",
                article_analysis=state.article_analysis or "N/A",
                user_request=state.user_request or "N/A",
                has_existing_readme=str(not existing_is_empty),
            ),
            parser=DiagnosisLLMOutput,
        )
        generation_mode = diagnosis.generation_mode
        target_sections = diagnosis.target_sections
        generation_plan = diagnosis.generation_plan or ""
    except (JsonParseError, ValidationError):
        logger.warning("[Diagnosis] LLM output failed validation after retries; using defaults.")
        generation_mode = "full_regen"
        target_sections = []
        generation_plan = "Fallback: using heuristic-based mode selection."

    logger.info(
        "[Diagnosis] mode=%s, readme_mode=%s, targets=%s",
        generation_mode, readme_mode, target_sections,
    )
    return {
        "readme_mode": readme_mode,
        "generation_mode": generation_mode,
        "target_sections": target_sections,
        "generation_plan": generation_plan,
    }
